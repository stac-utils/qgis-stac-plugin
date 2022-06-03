import os
import typing
import uuid

from dateutil import parser

from json.decoder import JSONDecodeError

from qgis.core import (
    QgsApplication,
    QgsTask,
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
    TemporalExtent
)

from ..lib import planetary_computer as pc

from pystac_client import Client
from pystac_client.exceptions import APIError

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
        except (APIError, NotImplementedError, JSONDecodeError) as err:
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
            providers = []
            for provider in collection.providers:
                resource_provider = ResourceProvider(
                    name=provider.name,
                    description=provider.description,
                    roles=provider.roles,
                    url=provider.url
                )
                providers.append(resource_provider)
            links = []
            for link in collection.links:
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
            spatial = vars(collection.extent.spatial)
            bbox = spatial.get('bbox') \
                if 'bbox' in spatial.keys() else spatial.get('bboxes')

            temporal = vars(collection.extent.temporal)
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

            # Avoid Attribute error and assign None to properties that are not available
            collection_dict = vars(collection)
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
                links=links,
                extent=extent,
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

        key = os.getenv(SAS_SUBSCRIPTION_VARIABLE)

        # If the plugin defined connection sas subscription key
        # exists use it instead of the environment one.
        connection = settings_manager.get_current_connection()

        if connection and \
            connection.capability == ApiCapability.SUPPORT_SAS_TOKEN and \
                connection.sas_subscription_key:
            key = connection.sas_subscription_key

        if key:
            pc.set_subscription_key(key)

        for item in items_list:
            # For APIs that support usage of SAS token we sign the whole item
            # so that the item assets can be accessed.
            if self.api_capability == ApiCapability.SUPPORT_SAS_TOKEN:
                item = pc.sign(item)
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
