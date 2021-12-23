import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import warnings

from functools import singledispatch
from urllib.parse import urlparse
import requests
from pydantic import BaseModel, Field
from pystac import Asset, Item, ItemCollection
from pystac.utils import datetime_to_str
from pystac_client import ItemSearch

from planetary_computer.settings import Settings
from planetary_computer.utils import (
    parse_blob_url,
    parse_adlfs_url,
    is_fsspec_asset,
    is_vrt_string,
    asset_xpr,
)


BLOB_STORAGE_DOMAIN = ".blob.core.windows.net"


class SASBase(BaseModel):
    """Base model for responses."""

    expiry: datetime = Field(alias="msft:expiry")
    """RFC339 datetime format of the time this token will expire"""

    class Config:
        json_encoders = {datetime: datetime_to_str}
        allow_population_by_field_name = True


class SignedLink(SASBase):
    """Signed SAS URL response"""

    href: str
    """The HREF in the format of a URL that can be used in HTTP GET operations"""


class SASToken(SASBase):
    """SAS Token response"""

    token: str
    """The Shared Access (SAS) Token that can be used to access the data
    in, for example, Azure's Python SDK"""

    def sign(self, href: str) -> SignedLink:
        """Signs an href with this token"""
        return SignedLink(href=f"{href}?{self.token}", expiry=self.expiry)

    def ttl(self) -> float:
        """Number of seconds the token is still valid for"""
        return (self.expiry - datetime.now(timezone.utc)).total_seconds()


# Cache of signing requests so we can reuse them
# Key is the signing URL, value is the SAS token
TOKEN_CACHE: Dict[str, SASToken] = {}


@singledispatch
def sign(obj: Any) -> Any:
    """Sign the relevant URLs belonging to any supported object with a
    Shared Access (SAS) Token, which allows for read access.

    Args:
        obj (Any): The object to sign. Must be one of:
            str (URL), Asset, Item, ItemCollection, or ItemSearch
    Returns:
        Any: A copy of the object where all relevant URLs have been signed
    """
    raise TypeError(
        "Invalid type, must be one of: str, Asset, Item, ItemCollection, or ItemSearch"
    )


@sign.register(str)
def sign_string(url: str) -> str:
    """Sign a URL or VRT-like string containing URLs with a Shared Access (SAS) Token

    Signing with a SAS token allows read access to files in blob storage.

    Args:
        url (str): The HREF of the asset as a URL or a GDAL VRT

            Single URLs can be found on a STAC Item's Asset ``href`` value. Only URLs to
            assets in Azure Blob Storage are signed, other URLs are returned unmodified.

            GDAL VRTs can combine many data sources into a single mosaic. A VRT can be
            built quickly from the GDAL STACIT driver
            https://gdal.org/drivers/raster/stacit.html. Each URL to Azure Blob Storage
            within the VRT is signed.

    Returns:
        str: The signed HREF or VRT
    """
    if is_vrt_string(url):
        return sign_vrt_string(url)
    else:
        return sign_url(url)


def sign_url(url: str) -> str:
    """Sign a URL or with a Shared Access (SAS) Token

    Signing with a SAS token allows read access to files in blob storage.

    Args:
        url (str): The HREF of the asset as a URL

            Single URLs can be found on a STAC Item's Asset ``href`` value. Only URLs to
            assets in Azure Blob Storage are signed, other URLs are returned unmodified.

    Returns:
        str: The signed HREF
    """
    parsed_url = urlparse(url.rstrip("/"))
    if not parsed_url.netloc.endswith(BLOB_STORAGE_DOMAIN):
        return url

    account, container = parse_blob_url(parsed_url)
    token = get_token(account, container)
    return token.sign(url).href


def _repl_vrt(m: re.Match) -> str:
    # replace all blob-storages URLs with a signed version.
    return sign_url(m.string[slice(*m.span())])


def sign_vrt_string(vrt: str) -> str:
    """Sign a VRT-like string containing URLs with a Shared Access (SAS) Token

    Signing with a SAS token allows read access to files in blob storage.

    Args:
        vrt (str): The GDAL VRT

            GDAL VRTs can combine many data sources into a single mosaic. A VRT can be
            built quickly from the GDAL STACIT driver
            https://gdal.org/drivers/raster/stacit.html. Each URL to Azure Blob Storage
            within the VRT is signed.

    Returns:
        str: The signed VRT

    Examples
    --------
    >>> from osgeo import gdal
    >>> from pathlib import Path
    >>> search = (
    ...     "STACIT:\"https://planetarycomputer.microsoft.com/api/stac/v1/search?"
    ...     "collections=naip&bbox=-100,40,-99,41"
    ...     "&datetime=2019-01-01T00:00:00Z%2F..\":asset=image"
    ... )
    >>> gdal.Translate("out.vrt", search)
    >>> signed_vrt = planetary_computer.sign(Path("out.vrt").read_text())
    >>> print(signed_vrt)
    <VRTDataset rasterXSize="161196" rasterYSize="25023">
    ...
    </VRTDataset>
    """
    return asset_xpr.sub(_repl_vrt, vrt)


@sign.register(Item)
def sign_item(item: Item) -> Item:
    """Sign all assets within a PySTAC item

    Args:
        item (Item): The Item whose assets that will be signed

    Returns:
        Item: A new copy of the Item where all assets' HREFs have
        been replaced with a signed version. In addition, a "msft:expiry"
        property is added to the Item properties indicating the earliest
        expiry time for any assets that were signed.
    """
    signed_item = item.clone()
    for key in signed_item.assets:
        _sign_asset_in_place(signed_item.assets[key])
    return signed_item


@sign.register(Asset)
def sign_asset(asset: Asset) -> Asset:
    """Sign a PySTAC asset

    Args:
        asset (Asset): The Asset to sign

    Returns:
        Asset: A new copy of the Asset where the HREF is replaced with a
        signed version.
    """
    return _sign_asset_in_place(asset.clone())


def _sign_asset_in_place(asset: Asset) -> Asset:
    """Sign a PySTAC asset

    Args:
        asset (Asset): The Asset to sign in place

    Returns:
        Asset: Input Asset object modified in place: the HREF is replaced
        with a signed version.
    """
    asset.href = sign(asset.href)
    if is_fsspec_asset(asset):
        key: Optional[str]

        for key in ["table:storage_options", "xarray:storage_options"]:
            if key in asset.extra_fields:
                break
        else:
            key = None

        if key:
            storage_options = asset.extra_fields[key]
            account = storage_options.get("account_name")
            container = parse_adlfs_url(asset.href)
            if account and container:
                token = get_token(account, container)
                asset.extra_fields[key]["credential"] = token.token
    return asset


def sign_assets(item: Item) -> Item:
    warnings.warn(
        "'sign_assets' is deprecated and will be removed in a future version. Use "
        "'sign_item' instead.",
        FutureWarning,
        stacklevel=2,
    )
    return sign_item(item)


@sign.register(ItemCollection)
def sign_item_collection(item_collection: ItemCollection) -> ItemCollection:
    """Sign a PySTAC item collection

    Args:
        item_collection (ItemCollection): The ItemCollection whose assets will be signed

    Returns:
        ItemCollection: A new copy of the ItemCollection where all assets'
        HREFs for each item have been replaced with a signed version. In addition,
        a "msft:expiry" property is added to the Item properties indicating the
        earliest expiry time for any assets that were signed.
    """
    new = item_collection.clone()
    for item in new:
        for key in item.assets:
            _sign_asset_in_place(item.assets[key])
    return new


@sign.register(ItemSearch)
def _search_and_sign(search: ItemSearch) -> ItemCollection:
    """Perform a PySTAC Client search, and sign the resulting item collection

    Args:
        search (ItemSearch): The ItemSearch whose resulting item assets will be signed

    Returns:
        ItemCollection: The resulting ItemCollection of the search where all assets'
        HREFs for each item have been replaced with a signed version. In addition,
        a "msft:expiry" property is added to the Item properties indicating the
        earliest expiry time for any assets that were signed.
    """
    return sign(search.get_all_items())


def get_token(account_name: str, container_name: str) -> SASToken:
    """
    Get a token for a container in a storage account.

    This will use a token from the cache if it's present and not too close
    to expiring. The generated token will be placed in the token cache.

    Args:
        account_name (str): The storage account name.
        container_name (str): The storage container name.
    Returns:
        SASToken: the generated token
    """
    settings = Settings.get()
    token_request_url = f"{settings.sas_url}/{account_name}/{container_name}"
    token = TOKEN_CACHE.get(token_request_url)

    # Refresh the token if there's less than a minute remaining,
    # in order to give a small amount of buffer
    if not token or token.ttl() < 60:
        headers = (
            {"Ocp-Apim-Subscription-Key": settings.subscription_key}
            if settings.subscription_key
            else None
        )
        response = requests.get(token_request_url, headers=headers)
        response.raise_for_status()
        token = SASToken(**response.json())
        if not token:
            raise ValueError(f"No token found in response: {response.json()}")
        TOKEN_CACHE[token_request_url] = token
    return token
