
from base import BaseClient


class Client(BaseClient):

    def handle_items(
            self,
            items
    ):
        self.items_received.emit(items, None)

    def handle_collections(
            self,
            collections
    ):
        self.items_received.emit(collections, None)

    def handle_error(
            self,
            message: str
    ):
        self.error_received.emit(message)
