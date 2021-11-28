
import typing

from qgis.PyQt import (
    QtCore,
)

from qgis.core import (
    QgsApplication,
    QgsTask,
)

import models

from ..lib.pystac_client import Client


class ContentFetcherTask(QgsTask):
    """
    Task to manage the STAC API content search using the pystac_client library,
    passes the found content to a provided response handler
    once fetching has finished.
    """

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
        super().__init__()
        self.url = url
        self.search_params = search_params
        self.resource_type = resource_type
        self.response_handler = response_handler
        self.error_handler = error_handler

    def run(self):
        """
        Runs the main task operation in the background.

        :returns: Whether the task completed successfully
        :rtype: bool
        """
        self.client = Client.open(self.url)
        if self.resource_type ==\
                models.ResourceType.FEATURE:
            self.response = self.client.search(
                **self.search_params.params()
            )
        elif self.resource_type == \
                models.ResourceType.COLLECTION:
            self.response = self.client.get_collections()
        else:
            raise NotImplementedError

        return self.response is not None

    def finished(self, result: bool):
        """
        Called after the task run() completes either successfully
        or upon early termination.

        :param result: Whether task completed with success
        :type result: bool
        """
        if result:
            self.response_handler(self.response)
        else:
            message = f"Error fetching content for {self.url!r}"
            self.error_handler(message)
