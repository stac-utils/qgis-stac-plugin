import typing

from qgis.PyQt import (
    QtCore,
    QtNetwork,
    QtXml
)

from qgis.core import QgsApplication

from .models import (
    ApiCapability,
    ItemSearch,
    ResourcePagination,
    ResourceType,
)

from .network import ContentFetcherTask
from ..conf import ConnectionSettings

from ..lib.pystac import ItemCollection


class BaseClient(QtCore.QObject):
    """ Base API client, defines main plugin content fetching operations
    for the STAC APIs.
    Inherits from QObject in order to leverage signal and slots mechanism.
    """
    auth_config: str
    url: str
    content_task: ContentFetcherTask
    capability: ApiCapability

    conformance_received = QtCore.pyqtSignal(
        list,
        ResourcePagination
    )

    collections_received = QtCore.pyqtSignal(
        list,
        ResourcePagination
    )
    items_received = QtCore.pyqtSignal(
        list,
        ResourcePagination
    )
    item_collections_received = QtCore.pyqtSignal(
        ItemCollection
    )
    error_received = QtCore.pyqtSignal([str], [str, int, str])

    def __init__(
            self,
            url: str,
            *args,
            auth_config: typing.Optional[str] = None,
            capability=None,
            **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.auth_config = auth_config or ""
        self.url = url.rstrip("/")
        self.content_task = None
        self.capability = capability

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
            capability=connection_settings.capability
        )

    def get_items(
        self,
        item_search: typing.Optional[ItemSearch] = None
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
            api_capability=self.capability,
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

    def get_conformance(
        self
    ):
        """Fetches the available conformance classes in the STAC API defined in this
        base client.
        """
        self.content_task = ContentFetcherTask(
            url=self.url,
            search_params=None,
            resource_type=ResourceType.CONFORMANCE,
            response_handler=self.handle_conformance,
            error_handler=self.handle_error,
        )

        QgsApplication.taskManager().addTask(self.content_task)

    def handle_conformance(
            self,
            conformance,
            pagination
    ):
        raise NotImplementedError

    def handle_collections(
            self,
            collections,
            pagination
    ):
        raise NotImplementedError

    def handle_items(
            self,
            items,
            pagination
    ):
        raise NotImplementedError

    def handle_item_collections(
            self,
            items
    ):
        raise NotImplementedError

    def handle_error(
            self,
            message: str
    ):
        raise NotImplementedError
