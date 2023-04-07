import os
import typing
import uuid
import json

from dateutil import parser
from functools import partial

from json.decoder import JSONDecodeError

from qgis.core import (
    QgsApplication,
    QgsNetworkContentFetcherTask,
    QgsTask,
)

from qgis.PyQt import (
    QtGui,
    QtCore,
    QtWidgets,
    QtNetwork
)

from .models import (
    ApiCapability,
    Conformance,
    Collection,
    Constants,
    Item,
    ItemSearch,
    ResourceAsset,
    ResourceExtent,
    ResourceLink,
    ResourcePagination,
    ResourceProperties,
    ResourceProvider,
    ResourceType,
    SpatialExtent,
    TemporalExtent,
    Queryable,
    QueryableProperty,
    QueryableFetchType
)

from ..lib import planetary_computer as pc

from pystac_client import Client
from pystac_client.exceptions import APIError

from pystac.errors import STACTypeError

from ..utils import log, tr

from ..conf import settings_manager
from ..definitions.constants import SAS_SUBSCRIPTION_VARIABLE


class ContentFetcherTask(QgsTask):
    """
    Task to manage the STAC API content search using the pystac_client library,
    passes the found content to a provided response handler
    once fetching has finished.
    """

    url: str
    search_params: ItemSearch
    resource_type: ResourceType
    api_capability: ApiCapability
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
            api_capability: ApiCapability = None,
            response_handler: typing.Callable = None,
            error_handler: typing.Callable = None,
    ):
        super().__init__()
        self.url = url
        self.search_params = search_params
        self.resource_type = resource_type
        self.api_capability = api_capability
        self.response_handler = response_handler
        self.error_handler = error_handler

    def run(self):
        """
        Runs the main task operation in the background.

        :returns: Whether the task completed successfully
        :rtype: bool
        """
        try:
            self.client = Client.open(self.url)
            if self.resource_type == \
                    ResourceType.FEATURE:
                if self.search_params:
                    response = self.client.search(
                        **self.search_params.params()
                    )
                else:
                    response = self.client.search()
                self.response = self.prepare_items_results(
                    response
                )

            elif self.resource_type == \
                    ResourceType.COLLECTION:
                if self.search_params and self.search_params.get('collection_id'):
                    response = self.client.get_collection(
                        self.search_params.get('collection_id')
                    )
                    self.response = self.prepare_collection_result(
                        response
                    )
                else:
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
        except (
                APIError,
                NotImplementedError,
                JSONDecodeError,
                STACTypeError
        ) as err:
            log(str(err))
            self.error = str(err)

        return self.response is not None

    def prepare_collection_result(
            self,
            collection_response
    ):
        """ Prepares the collection result

          :param collection_response: Collection
          :type collection_response: pystac_client.CollectionClient

          :returns: Collection instance
          :rtype: Collection
          """

        spatial = vars(collection_response.extent.spatial)
        bbox = spatial.get('bbox') \
            if 'bbox' in spatial.keys() else spatial.get('bboxes')

        temporal = vars(collection_response.extent.temporal)
        interval = temporal.get('interval') \
            if 'bbox' in spatial.keys() else spatial.get('intervals')
        spatial_extent = SpatialExtent(
            bbox=bbox
        )
        temporal_extent = TemporalExtent(
            interval=interval
        )

        extent = ResourceExtent(
            spatial=spatial_extent,
            temporal=temporal_extent
        )

        links = []

        for link in collection_response.links:
            link_dict = vars(link)
            link_type = link_dict.get('type') \
                if 'type' in link_dict.keys() \
                else link_dict.get('media_type')
            resource_link = ResourceLink(
                href=link.href,
                rel=link.rel,
                title=link.title,
                type=link_type
            )
            links.append(resource_link)

        providers = []
        for provider in collection_response.providers or []:
            resource_provider = ResourceProvider(
                name=provider.name,
                description=provider.description,
                roles=provider.roles,
                url=provider.url
            )
            providers.append(resource_provider)

        # Avoid Attribute error and assign None to
        # properties that are not available.
        collection_dict = vars(collection_response)
        id = collection_dict.get('id', None)
        title = collection_dict.get('title', None)
        description = collection_dict.get('description', None)
        keywords = collection_dict.get('keywords', None)
        license = collection_dict.get('license', None)
        stac_version = collection_dict.get('stac_version', None)
        summaries = collection_dict.get('summaries', None)

        collection_result = Collection(
            id=id,
            title=title,
            description=description,
            keywords=keywords,
            license=license,
            stac_version=stac_version,
            summaries=summaries,
            extent=extent,
            links=links,
            providers=providers,
        )

        return collection_result

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
            # Avoid Attribute error and assign None to properties that are not available
            collection_dict = vars(collection)
            id = collection_dict.get('id', None)
            title = collection_dict.get('title', None)

            collection_result = Collection(
                id=id,
                title=title,
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
        page = self.search_params.page \
            if self.search_params else Constants.PAGE_SIZE
        while True:
            try:
                collection = next(items_generator)
                prev_collection = collection
                if page == count:
                    items_collection = collection
                    break
                count += 1
            except StopIteration:
                self.pagination.total_pages = count
                items_collection = prev_collection
                break
        items = self.get_items_list(items_collection)
        return items

    def get_items_list(self, items_collection):
        """ Gets and prepares the items list from the
        pystac-client Collection generator

        :param items_collection: The STAC item collection generator
        :type items_collection: pystac_client.CollectionClient

        :returns: List of items
        :rtype: models.Item
        """
        items = []
        properties = None
        items_list = items_collection.items if items_collection else []

        for item in items_list:
            try:
                properties_datetime = item.properties.get("datetime")

                item_datetime = parser.parse(
                    properties_datetime
                ) if properties_datetime else None

                properties_start_date = item.properties.get("start_date")
                start_date = parser.parse(
                    properties_start_date,
                ) if properties_start_date else None

                properties_end_date = item.properties.get("end_date")

                end_date = parser.parse(
                    properties_end_date
                ) if properties_end_date else None

                cloud_cover = item.properties.get("eo:cloud_cover")

                properties = ResourceProperties(
                    resource_datetime=item_datetime,
                    eo_cloud_cover=cloud_cover,
                    start_date=start_date,
                    end_date=end_date
                )
            except Exception as e:
                log(
                    f"Error in parsing item properties datetime"
                )
            assets = []
            for key, asset in item.assets.items():
                title = asset.title if asset.title else key
                item_asset = ResourceAsset(
                    href=asset.href,
                    title=title,
                    description=asset.description,
                    type=asset.media_type,
                    roles=asset.roles or []
                )
                assets.append(item_asset)
            item_result = Item(
                id=item.id,
                item_uuid=uuid.uuid4(),
                properties=properties,
                collection=item.collection_id,
                assets=assets,
                stac_object=item,

            )
            if item.geometry:
                item_result.geometry = item.geometry
            items.append(item_result)

        return items

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
            conformance_instance = Conformance(
                id=uuid.uuid4(),
                name=name,
                uri=uri,
            )
            conformance_classes.append(conformance_instance)

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


class NetworkFetcher(QtCore.QObject):
    """
    Handles fetching of STAC API resources that are not available
    via the pystac_client library
    """

    url: str
    response_handler: typing.Callable
    error_handler: typing.Callable

    def __init__(
            self,
            url,
            response_handler,
            error_handler
    ):
        self.url = url
        self.response_handler = response_handler
        self.error_handler = error_handler
        self.response_data = None

    def get_queryable(self, fetch_type, resource):
        """ Fetches the catalog queryable properties"""

        if fetch_type == QueryableFetchType.CATALOG:
            endpoint = "queryables"
        elif fetch_type == QueryableFetchType.COLLECTION:
            endpoint = f"collections/{resource}/queryables"
        else:
            raise NotImplementedError

        url = f"{self.url.strip('/')}/{endpoint}"
        request = QtNetwork.QNetworkRequest(
            QtCore.QUrl(
                url
            )
        )
        self.network_task(
            request,
            self.queryable_response,
            self.error_handler
        )

    def queryable_response(self, content):
        """ Callback to handle the queryable properties
        network response.

        :param content: Network response data
        :type content: QByteArray
        """
        self.response_handler(content)

    def network_task(
            self,
            request,
            handler,
            error_handler,
            auth_config=""
    ):
        """Fetches the response from the given request.

        :param request: Network request
        :type request: QNetworkRequest

        :param handler: Callback function to handle the response
        :type handler: Callable

        :param auth_config: Authentication configuration string
        :type auth_config: str
        """
        task = QgsNetworkContentFetcherTask(
            request,
            authcfg=auth_config
        )
        response_handler = partial(
            self.response,
            task,
            handler,
            error_handler

        )
        task.fetched.connect(response_handler)
        task.run()

    def response(
            self,
            task,
            handler,
            error_handler
    ):
        """ Handles the returned response

        :param task: QGIS task that fetches network content
        :type task:  QgsNetworkContentFetcherTask
        """
        reply = task.reply()
        error = reply.error()
        if error == QtNetwork.QNetworkReply.NoError:
            contents: QtCore.QByteArray = reply.readAll()
            try:
                data = json.loads(
                    contents.data().decode()
                )
                queryable = self.prepare_queryable(data)
                handler(queryable)
            except json.decoder.JSONDecodeError as err:
                log(tr("Problem parsing network response"))
        else:
            error_handler(tr("Problem fetching response from network"))

            log(tr("Problem fetching response from network"))

    def prepare_queryable(self, data):
        """ Prepares the passed data dict into a plugin Queryable instance.

        :param data: Response data
        :type data:  dict

        :returns: STAC queryable properties
        :rtype: Queryable
        """
        properties = []

        queryable_properties = data.get('properties', {})

        for key, value in queryable_properties.items():
            enum_values = value.get('enum')
            property_type = value.get('type')
            if enum_values:
                property_type = 'enum'
            if key == 'datetime':
                property_type = 'datetime'

            queryable_property = QueryableProperty(
                name=key,
                title=value.get('title'),
                description=value.get('description'),
                ref=value.get('$ref'),
                type=property_type,
                minimum=value.get('minimum'),
                maximum=value.get('maximum'),
                values=enum_values
            )
            properties.append(queryable_property)

        queryable = Queryable(
            schema=data.get('$schema'),
            id=data.get('id'),
            type=data.get('type'),
            title=data.get('title'),
            description=data.get('description'),
            properties=properties,
        )

        return queryable
