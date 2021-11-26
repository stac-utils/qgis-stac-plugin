import typing

from qgis.PyQt import (
    QtCore,
    QtNetwork,
    QtXml
)

import models

from network import ContentFetcherTask
from qgis_stac.conf import ConnectionSettings


class BaseClient(QtCore.QObject):
    auth_config: str
    url: str
    network_task: ContentFetcherTask

    collections_received = QtCore.pyqtSignal(
        list[models.Collection],
        models.ResourcePagination
    )
    items_received = QtCore.pyqtSignal(
        list[models.Item],
        models.ResourcePagination
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
        self.network_task = None

    @classmethod
    def from_connection_settings(
            cls,
            connection_settings: ConnectionSettings
    ):
        return cls(
            url=connection_settings.url,
            auth_config=connection_settings.auth_config,
        )

    def get_items(
        self,
        item_search: typing.Optional[models.ItemSearch] = None
    ):
        params = self.get_search_params(item_search)
        self.network_task = ContentFetcherTask(
            url=self.url,
            search_params=params,
            resource_type=models.ResourceType.FEATURE,
            response_handler=self.handle_items,
            error_handler=self.handle_error,
        )

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
