import typing

from qgis.PyQt import (
    QtCore,
    QtNetwork,
    QtXml
)

from qgis.core import QgsApplication

from .models import (
    Collection,
    Item,
    ItemSearch,
    ResourcePagination,
    ResourceType,
)

from .network import ContentFetcherTask
from ..conf import ConnectionSettings


class BaseClient(QtCore.QObject):
    """ Base API client, defines main plugin content fetching operations
    for the STAC APIs.
    Inherits from QObject in order to leverage signal and slots mechanism.
    """
    auth_config: str
    url: str
    content_task: ContentFetcherTask

    collections_received = QtCore.pyqtSignal(
        list,
        ResourcePagination
    )
    items_received = QtCore.pyqtSignal(
        list,
        ResourcePagination
    )
    error_received = QtCore.pyqtSignal([str], [str, int, str])

    def __init__(
            self,
            url: str,
            *args,
            auth_config: typing.Optional[str] = None,
            **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.auth_config = auth_config or ""
        self.url = url.rstrip("/")
        self.content_task = None

    @classmethod
    def from_connection_settings(
            cls,
            connection_settings: ConnectionSettings
    ):
        """Creates a BaseClient instance from the provided connections settings

        :param connection_settings: Connection details retrieved from the
        plugin settings
        :type connection_settings: ConnectionSettings

        :returns: Base client instance
        :rtype: BaseClient
        """
        return cls(
            url=connection_settings.url,
            auth_config=connection_settings.auth_config,
        )

    def get_items(
        self,
        item_search: typing.Optional[ItemSearch]
    ):
        """Searches for items in the STAC API defined in this
        base client.

        :param item_search: Search item object that contains fields
        used in querying the STAC items
        :type item_search: ItemSearch
        """
        self.content_task = ContentFetcherTask(
            url=self.url,
            search_params=item_search,
            resource_type=ResourceType.FEATURE,
            response_handler=self.handle_items,
            error_handler=self.handle_error,
        )

        QgsApplication.taskManager().addTask(self.content_task)

    def get_collections(
        self
    ):
        """Fetches all the collections in the STAC API defined in this
        base client.
        """
        self.content_task = ContentFetcherTask(
            url=self.url,
            search_params=None,
            resource_type=ResourceType.COLLECTION,
            response_handler=self.handle_collections,
            error_handler=self.handle_error,
        )

        QgsApplication.taskManager().addTask(self.content_task)

    def handle_collections(
            self,
            collections
    ):
        raise NotImplementedError

    def handle_items(
            self,
            items
    ):
        raise NotImplementedError

    def handle_error(
            self,
            message: str
    ):
        raise NotImplementedError
