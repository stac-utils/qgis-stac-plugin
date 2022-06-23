# -*- coding: utf-8 -*-

""" QGIS STAC API plugin API client

Definition of plugin base client subclass that deals
with post network response handling.
"""

from .base import BaseClient
from .models import (
    ResourcePagination,
)


class Client(BaseClient):
    """ API client class that provides implementation of the
    STAC API querying operations.
    """

    def handle_items(
            self,
            items_response,
            pagination
    ):
        """Emits the search results items, so plugin signal observers
        eg. gui can use the data.

        :param items_response: Search results items
        :type items_response: List[models.Items]

        :param pagination: Item results pagination details
        :type pagination: ResourcePagination
        """
        self.items_received.emit(items_response, pagination)

    def handle_item_collections(
            self,
            items_response,
            pagination
    ):
        """Emits the search results item collections generator

        :param items_response: Search results items
        :type items_response: List[models.Items]

        :param pagination: Item collections results pagination details
        :type pagination: ResourcePagination
        """
        self.item_collections_received.emit(
            items_response.get_item_collections(),
            pagination
        )

    def handle_collection(
            self,
            collection_response,
            pagination
    ):
        """Emits the search response collection.

        :param collection_response: Search result collection
        :type collection_response: models.Collection

        :param pagination: Collection results pagination details
        :type pagination: ResourcePagination
        """

        self.collection_received.emit(collection_response)

    def handle_collections(
            self,
            collections_response,
            pagination
    ):
        """Emits the search results collections.

        :param collections_response: Search results collections
        :type collections_response: List[models.Collection]

        :param pagination: Collection results pagination details
        :type pagination: ResourcePagination
        """

        # TODO query filter pagination results from the
        # response
        pagination = ResourcePagination()

        self.collections_received.emit(collections_response, pagination)

    def handle_conformance(
            self,
            conformance,
            pagination
    ):
        """Emits the fetched conformance classes from the API.

        :param conformance: Conformance classes
        :type conformance: list

        :param pagination: Conformance classes pagination details.
        :type pagination: ResourcePagination
        """
        self.conformance_received.emit(conformance, pagination)

    def handle_queryable(
            self,
            queryable
    ):
        """Emits the fetched queryable properties classes from the API.

        :param queryable: Queryable properties
        :type queryable: models.Queryable
        """
        self.queryable_received.emit(queryable)

    def handle_error(
            self,
            message: str
    ):
        """Emits the found error message from the network response.

        :param message: Error message
        :type message: str
        """
        self.error_received.emit(message)
