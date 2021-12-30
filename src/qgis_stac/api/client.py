import datetime
import typing

from .base import BaseClient
from .models import (
    ApiCapability,
    Collection,
    Item,
    ResourceAsset,
    ResourcePagination,
    ResourceProperties,
)

from ..utils import log
from ..lib.planetary_computer import sas


class Client(BaseClient):
    """ API client class that provides implementation of the
    STAC API querying operations.
        """
    def handle_items(
            self,
            items_response,
            pagination
    ):
        """Emits the search results items, so plugin signal observers
        eg. gui can use the data.

        :param items_response: Search results items
        :type items_response: List[models.Items]

        :param pagination: Item results pagination details
        :type pagination: ResourcePagination
        """
        items = []
        properties = None
        items_list = items_response.items if items_response else []
        for item in items_list:
            if self.capability == ApiCapability.SUPPORT_SAS_TOKEN:
                item = sas.sign(item)
            try:
                item_datetime = datetime.datetime.strptime(
                    item.properties.get("datetime"),
                    "%Y-%m-%dT%H:%M:%SZ"
                )
                properties = ResourceProperties(
                    resource_datetime=item_datetime
                )
            except (TypeError, ValueError) as e:
                log(
                    f"Error in passing item properties datetime, {str(e)}"
                )
                pass
            assets = []
            for key, asset in item.assets.items():
                item_asset = ResourceAsset(
                    href=asset.href,
                    title=asset.title,
                    description=asset.description,
                    type=asset.media_type,
                    roles=asset.roles or []
                )
                assets.append(item_asset)
            item_result = Item(
                id=item.id,
                properties=properties,
                collection=item.collection_id,
                assets=assets

            )
            if item.geometry:
                item_result.geometry = item.geometry
            items.append(item_result)

        self.items_received.emit(items, pagination)

    def handle_item_collections(
            self,
            items_response,
            pagination
    ):
        """Emits the search results item collections generator

        :param items_response: Search results items
        :type items_response: List[models.Items]

        :param pagination: Item collections results pagination details
        :type pagination: ResourcePagination
        """
        self.item_collections_received.emit(
            items_response.get_item_collections(),
            pagination
        )

    def handle_collections(
            self,
            collections_response,
            pagination
    ):
        """Emits the search results collections.

        :param collections_response: Search results collections
        :type collections_response: List[models.Collection]

        :param pagination: Collection results pagination details
        :type pagination: ResourcePagination
        """

        # TODO query filter pagination results from the
        # response
        pagination = ResourcePagination()

        self.collections_received.emit(collections_response, pagination)

    def handle_conformance(
            self,
            conformance,
            pagination
    ):
        """Emits the fetched conformance classes from the API.

        :param conformance: Conformance classes
        :type conformance: list

        :param pagination: Conformance classes pagination details.
        :type pagination: ResourcePagination
        """
        self.conformance_received.emit(conformance, pagination)

    def handle_error(
            self,
            message: str
    ):
        """Emits the found error message.

        :param message: Error message
        :type message: str
        """
        self.error_received.emit(message)
