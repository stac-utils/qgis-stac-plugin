import datetime

from .base import BaseClient
from .models import (
    Collection,
    Item,
    ResourceAsset,
    ResourcePagination,
    ResourceProperties,
)

from ..utils import log


class Client(BaseClient):
    """ API client class that provides implementation of the
    STAC API querying operations.
        """
    def handle_items(
            self,
            items_response
    ):
        """Emits the search results items, so plugin signal observers
        eg. gui can use the data.

        :param items_response: Search results items
        :type items_response: List[models.Items]
        """
        items = []
        pagination = ResourcePagination()
        properties = None
        for item in items_response.get_items():
            try:
                item_datetime = datetime.datetime.strptime(
                    item.properties.get("datetime"),
                    "%Y-%m-%dT%H:%M:%SZ"
                )
                properties = ResourceProperties(
                    resource_datetime=item_datetime
                )
            except (TypeError, ValueError) as e:
                log(f"Error in passing item properties datetime, {str(e)}")
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
            items.append(item_result)

        self.items_received.emit(items, pagination)

    def handle_collections(
            self,
            collections_response
    ):
        """Emits the search results collections.

        :param collections_response: Search results collections
        :type collections_response: List[models.Collection]
        """
        collections = []
        for collection in collections_response:
            collection_result = Collection(
                id=collection.id,
                title=collection.title
            )
            collections.append(collection_result)

        # TODO query filter pagination results from the
        # response
        pagination = ResourcePagination()

        self.collections_received.emit(collections, pagination)

    def handle_error(
            self,
            message: str
    ):
        """Emits the found error message.

        :param message: Error message
        :type message: str
        """
        self.error_received.emit(message)
