import re

from typing import Tuple, Optional
from urllib.parse import ParseResult, urlunparse, urlparse

import pystac


def parse_blob_url(parsed_url: ParseResult) -> Tuple[str, str]:
    """Find the account and container in a blob URL

    Parameters
    ----------
    url: str
        URL to extract information from

    Returns
    -------
    Tuple of the account name and container name
    """
    try:
        account_name = parsed_url.netloc.split(".")[0]
        path_blob = parsed_url.path.lstrip("/").split("/", 1)
        container_name = path_blob[-2]
    except Exception as failed_parse:
        raise ValueError(
            f"Invalid blob URL: {urlunparse(parsed_url)}"
        ) from failed_parse

    return account_name, container_name


def parse_adlfs_url(url: str) -> Optional[str]:
    """
    Extract the storage container from an adlfs URL.

    Parameters
    ----------
    url : str
        The URL to extract the container from, if present

    Returns
    -------
    str or None
        Returns the container name, if present. Otherwise None is returned.
    """
    if url.startswith(("abfs://", "az://")):
        return urlparse(url).netloc
    return None


def is_fsspec_asset(asset: pystac.Asset) -> bool:
    """
    Determine if an Asset points to an fsspec URL.

    This checks if "account_name" is present in the asset's "table:storage_options"
    or "xarray:storage_options" fields.
    """
    return "account_name" in asset.extra_fields.get(
        "table:storage_options", {}
    ) or "account_name" in asset.extra_fields.get("xarray:storage_options", {})


def is_vrt_string(s: str) -> bool:
    """
    Check whether a string looks like a VRT
    """
    return s.strip().startswith("<VRTDataset") and s.strip().endswith("</VRTDataset>")


asset_xpr = re.compile(
    r"https://(?P<account>[A-z0-9]+?)"
    r"\.blob\.core\.windows\.net/"
    r"(?P<container>.+?)"
    r"/(?P<blob>[^<]+)"
)
