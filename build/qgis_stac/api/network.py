
import typing

from qgis.PyQt import (
    QtCore,
)

from qgis.core import (
    QgsApplication,
    QgsTask,
)

from .models import (
    Collection,
    ItemSearch,
    ResourcePagination,
    ResourceType,
)

from pystac_client import Client
from pystac_client.exceptions import APIError

from ..utils import log


class ContentFetcherTask(QgsTask):
    """
    Task to manage the STAC API content search using the pystac_client library,
    passes the found content to a provided response handler
    once fetching has finished.
    """

    url: str
    search_params: ItemSearch
    resource_type: ResourceType
    response_handler: typing.Callable
    error_handler: typing.Callable

    response = None
    error = None
    client: Client = None

    def __init__(
        self,
        url: str,
        search_params: ItemSearch,
        resource_type: ResourceType,
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
        try:
            if self.resource_type == \
                    ResourceType.FEATURE:
                self.response = self.client.search(
                    **self.search_params.params()
                )
            elif self.resource_type == \
                    ResourceType.COLLECTION:
                self.response = self.client.get_collections()
            else:
                raise NotImplementedError
        except APIError as err:
            log(str(err))
            self.error = str(err)

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
            message = f"Problem in fetching content for {self.url!r}," \
                      f"Error {self.error}"
            self.error_handler(message)
