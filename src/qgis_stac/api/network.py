import re
import typing
import uuid

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

from ..lib.pystac_client import Client
from ..lib.pystac_client.conformance import ConformanceClasses
from ..lib.pystac_client.exceptions import APIError

from ..conf import ConformanceSettings

from ..utils import log, tr


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
    client = None
    pagination = None

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
                response = self.client.search(
                    **self.search_params.params()
                )
                self.response = self.prepare_items_results(
                    response
                )

            elif self.resource_type == \
                    ResourceType.COLLECTION:
                response = self.client.get_collections()
                self.response = self.prepare_collections_results(
                    response
                )

            elif self.resource_type == ResourceType.CONFORMANCE:
                if self.client._stac_io and \
                        self.client._stac_io._conformance:
                    self.response = self.prepare_conformance_results(
                        self.client._stac_io._conformance
                    )
                else:
                    self.error = tr("No conformance available")
                self.pagination = ResourcePagination()
            else:
                raise NotImplementedError
        except APIError as err:
            log(str(err))
            self.error = str(err)

        return self.response is not None

    def prepare_collections_results(
            self,
            collections_response
    ):
        """ Prepares the collections results

        :param collections_response: Collection generator
        :type collections_response: pystac_client.CollectionClient

        :returns: List of collections
        :rtype: list
        """
        collections = []
        for collection in collections_response:
            collection_result = Collection(
                id=collection.id,
                title=collection.title
            )
            collections.append(collection_result)
        return collections

    def prepare_items_results(self, response):
        """ Prepares the search items results

        :param response: Fetched response from the pystac-client library
        :type response: pystac_client.ItemSearch

        :returns: Collection of items in a list
        :rtype: list
        """
        self.pagination = ResourcePagination()
        count = 1
        items_generator = response.get_item_collections()
        prev_collection = None
        items_collection = None
        while True:
            try:
                collection = next(items_generator)
                prev_collection = collection
                if self.search_params.page == count:
                    items_collection = collection
                    break
                count += 1
            except StopIteration:
                self.pagination.total_pages = count
                items_collection = prev_collection
                break
        return items_collection

    def prepare_conformance_results(self, conformance):
        """ Prepares the fetched conformance classes

        :param conformance: Fetched list of the conformance classes  API
        :type conformance: list

        :returns: Conformance classes settings instance list
        :rtype: list
        """
        conformance_classes = []
        for uri in conformance:
            parts = uri.split('/')
            name = parts[len(parts) - 1]
            conformance_settings = ConformanceSettings(
                id=uuid.uuid4(),
                name=name,
                uri=uri,
            )
            conformance_classes.append(conformance_settings)

        return conformance_classes

    def finished(self, result: bool):
        """
        Called after the task run() completes either successfully
        or upon early termination.

        :param result: Whether task completed with success
        :type result: bool
        """
        if result:
            self.response_handler(self.response, self.pagination)
        else:
            message = tr("Problem in fetching content for {}."
                         "Error details, {}").format(self.url, self.error)
            self.error_handler(message)
