import dataclasses
import typing

from functools import partial

from qgis.PyQt import (
    QtCore,
    QtNetwork,
    QtXml
)

from qgis.core import (
    QgsApplication,
    QgsNetworkContentFetcherTask,
    QgsTask,
)

import models

from qgis_stac.lib.pystac_client import Client


class BaseClient(QtCore.QObject):
    auth_config: str
    url: str
    network_task: NetworkFetchTask

    collections_received = QtCore.pyqtSignal(list, models.ResourcePagination)
    items_received = QtCore.pyqtSignal(list, models.ResourcePagination)
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
            connection_settings: "ConnectionSettings"
    ):
        return cls(
            url=connection_settings.url,
            auth_config=connection_settings.auth_config,
        )

    def get_items(
        self,
        item_search: typing.Optional[models.ItemSearch] = None
    ):
        url = self.get_item_search_url(item_search)
        request = QtNetwork.QNetworkRequest(url)
        self.network_task = NetworkFetchTask(
            url=self.url,
            search_params=item_search,
            resource_type=models.ResourceType.FEATURE,
            response_handler=self.handle_items(),
            error_handler=self.handle_error(),
        )

    def handle_items(
            self,
            payload: typing.Any
    ):
        raise NotImplementedError

    def handle_error(
            self,
            message: str
    ):
        raise NotImplementedError


class NetworkFetchTask(QgsTask):

    url: str
    search_params: models.ItemSearch
    resource_type: models.ResourceType
    response_handler: typing.Callable
    error_handler: typing.Callable

    response: QtCore.QByteArray = None
    client: Client = None

    def __init__(
        self,
        url: str,
        search_params: models.ItemSearch,
        resource_type: models.ResourceType,
        response_handler: typing.Callable = None,
        error_handler: typing.Callable = None,
    ):
        """
        """
        super().__init__()
        self.url = url
        self.search_params = search_params
        self.resource_type = resource_type
        self.response_handler = response_handler
        self.error_handler = error_handler

    def run(self):
        self.client = Client.open(self.url)
        if self.resource_type ==\
                models.ResourceType.FEATURE:
            self.response = self.client.search(
                self.search_params.to_dict())
        elif self.resource_type == \
                models.ResourceType.COLLECTION:
            self.response = self.client.get_collections()
        else:
            raise NotImplementedError

        return self.response is not None

    def finished(self, result: bool):
        if result:
            self.response_handler(self.response)
        else:
            message = f"Error fetching content for {self.url!r}"
            self.error_handler(message)
