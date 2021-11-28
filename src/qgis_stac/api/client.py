
from .base import BaseClient


class Client(BaseClient):
    """ API client class that provides implementation of the
    STAC API querying operations.
        """
    def handle_items(
            self,
            items
    ):
        """Emits the search results items, so plugin signal observers
        eg. gui can use the data.

        :param items: Search results items
        :type items: List[models.Items]
        """
        self.items_received.emit(items, None)

    def handle_collections(
            self,
            collections
    ):
        """Emits the search results collections.

        :param collections: Search results collections
        :type collections: List[models.Collection]
        """
        self.items_received.emit(collections, None)

    def handle_error(
            self,
            message: str
    ):
        """Emits the found error message.

        :param message: Error message
        :type message: str
        """
        self.error_received.emit(message)
