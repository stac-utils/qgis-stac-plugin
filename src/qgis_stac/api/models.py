# -*- coding: utf-8 -*-
""" QGIS STAC API plugin models

The STAC API related resources have been defined
in accordance to their definition available on
https://github.com/radiantearth/stac-api-spec/tree/master/stac-spec

"""

import dataclasses
import datetime
import enum
import json
import typing

from uuid import UUID, uuid4

from qgis.PyQt import (
    QtCore
)

from qgis.core import QgsRectangle

from ..lib.pystac.item import Item as STACObject


@dataclasses.dataclass
class ResourcePagination:
    """The plugin resource pagination for the search results"""
    total_items: int = 0
    total_pages: int = 0
    current_page: int = 1
    page_size: int = 10
    next_page: str = None
    previous_page: str = None


class ApiCapability(enum.Enum):
    SUPPORT_SAS_TOKEN = "Support SAS Token"


class AssetRoles(enum.Enum):
    """ STAC Item assets roles defined as outlined in
    https://github.com/radiantearth/stac-api-spec/blob/
    master/stac-spec/item-spec/item-spec.md#asset-roles
    """
    THUMBNAIL = 'thumbnail'
    OVERVIEW = 'overview'
    DATA = 'data'
    METADATA = 'metadata'


class AssetLayerType(enum.Enum):
    """ Types of assets layers that can be added to QGIS, values are defined as in
    https://github.com/radiantearth/stac-api-spec/blob/
    master/stac-spec/best-practices.md#common-media-types-in-stac"""
    COG = 'image/tiff; application=geotiff; profile=cloud-optimized'
    COPC = 'application/vnd.laszip+copc'
    GEOTIFF = 'image/tiff; application=geotiff'
    GEOJSON = 'application/geo+json'
    GEOPACKAGE = 'application/geopackage+sqlite3'
    VECTOR = 'ogr'
    NETCDF = 'application/netcdf; application/x-netcdf'


class Constants(enum.Enum):
    """ Default plugin constants"""
    PAGE_SIZE = 10


class FilterLang(enum.Enum):
    """ Filter languages that can be used to filter items during
    STAC API item search
    """
    CQL_TEXT = 'CQL_TEXT'
    CQL2_TEXT = 'CQL2_TEXT'
    CQL_JSON = 'CQL_JSON'
    CQL2_JSON = 'CQL2_JSON'
    STAC_QUERY = 'STAC_QUERY'


class FilterOperator(enum.Enum):
    """ Filter text operators.
    """
    LESS_THAN = '<'
    GREATER_THAN = '>'
    LESS_THAN_EQUAL = '<='
    GREATER_THAN_EQUAL = '>='
    EQUAL = '='


class QueryablePropertyType(enum.Enum):
    """ Represents STAC queryable property types."""
    INTEGER = 'integer'
    STRING = 'string'
    OBJECT = 'object'
    ENUM = 'enum'
    DATETIME = 'datetime'

class SortField(enum.Enum):
    """ Holds the field value used when sorting items results."""
    ID = 'ID'
    COLLECTION = 'COLLECTION'
    DATE = 'DATE'


class SortOrder(enum.Enum):
    """ Holds the ordering value when sorting items results."""
    ASCENDING = 'ASCENDING'
    DESCENDING = 'DESCENDING'


class SortOrderPrefix(enum.Enum):
    """ Holds the STAC ordering prefix value when sorting items results."""
    ASCENDING = '+'
    DESCENDING = '-'


class TimeUnits(enum.Enum):
    """ Represents time units."""
    SECONDS = 'SECONDS'
    MINUTES = 'MINUTES'
    HOURS = 'HOURS'
    DAYS = 'DAYS'


class GeometryType(enum.Enum):
    """Enum to represent the available geometry types """

    POINT = "Point"
    LINESTRING = "LineString"
    POLYGON = "Polygon"
    MULTIPOINT = "MultiPoint"
    MULTILINESTRING = "MultiLineString"
    MULTIPOLYGON = "MultiPolygon"


class ResourceType(enum.Enum):
    """Represents the STAC API resource types """
    COLLECTION = "Collection"
    FEATURE = "Feature"
    CATALOG = "Catalog"
    CONFORMANCE = "Conformance"


class QueryableFetchType(enum.Enum):
    """Queryable fetch types"""
    CATALOG = "Catalog"
    COLLECTION = "Collection"
    COLLECTIONS = "Collections"


@dataclasses.dataclass
class SpatialExtent:
    """Spatial extent as defined by the STAC API"""
    bbox: typing.List[int]


@dataclasses.dataclass
class TemporalExtent:
    """Temporal extent as defined by the STAC API"""
    interval: typing.List[str]


@dataclasses.dataclass
class ResourceAsset:
    """The STAC API asset"""
    href: str
    title: str
    description: str
    type: str
    roles: typing.List[str]
    name: str = None
    downloaded: bool = False


@dataclasses.dataclass
class ResourceExtent:
    """The STAC API extent"""
    spatial: SpatialExtent
    temporal: TemporalExtent


@dataclasses.dataclass
class ResourceLink:
    """The STAC API link resource"""
    href: str
    rel: str
    title: str
    type: str


@dataclasses.dataclass
class ResourceProperties:
    """Represents the STAC API Properties object,
    which contains additional metadata fields
    for the STAC API resources.
    """
    title: str = None
    description: str = None
    resource_datetime: datetime.datetime = None
    created: datetime.datetime = None
    updated: datetime.datetime = None
    start_date: datetime.datetime = None
    end_date: datetime.datetime = None
    license: str = None
    eo_cloud_cover: float = None


@dataclasses.dataclass
class ResourceProvider:
    """Represents the STAC API Provider object,
    which contains information about the provider that
    captured the content available on a STAC API collections.
    """
    name: str
    description: str
    roles: [str]
    url: str


# TODO Update the geometry coordinates type to include
# all geometry types
class ResourceGeometry:
    """The GeoJSON geometry footprint STAC API assets"""
    type: GeometryType
    coordinates: typing.List[typing.List[int]]


@dataclasses.dataclass
class QueryableProperty:
    """Represents the STAC API queryable properties, from
    https://github.com/radiantearth/stac-api-spec/blob/master/
    fragments/filter/README.md#queryables
    """
    name: str
    title: str
    type: str
    ref: str
    description: str
    minimum: str
    maximum: str
    values: list


@dataclasses.dataclass
class Queryable:
    """Represents the STAC API queryable properties, defined from
    https://github.com/radiantearth/stac-api-spec/blob/master/
    fragments/filter/README.md#queryables
    """
    schema: str = None
    id: str = None
    type: str = None
    title: str = None
    description: str = None
    properties: typing.List[QueryableProperty] = None


@dataclasses.dataclass
class Catalog:
    """ Represents the STAC API Catalog"""
    id: int
    uuid: UUID
    title: str
    description: str
    type: ResourceType
    stac_version: str
    stac_extensions: typing.List[str]
    links: typing.List[ResourceLink]


@dataclasses.dataclass
class Collection:
    """ Represents the STAC API Collection"""
    id: str = None
    uuid: UUID = None
    title: str = None
    description: str = None
    keywords: typing.List[str] = None
    license: str = None
    type: ResourceType = None
    stac_version: str = None
    stac_extensions: typing.List[str] = None
    links: typing.List[ResourceLink] = None
    assets: typing.Dict[str, ResourceAsset] = None
    providers: typing.List[ResourceProvider] = None
    extent: ResourceExtent = None
    summaries: typing.Dict[str, str] = None


@dataclasses.dataclass
class Conformance:
    """ Represents the stored plugin conformance class"""

    id: UUID = None
    name: str = None
    uri: str = None


@dataclasses.dataclass
class Item:
    """ Represents the plugin STAC API Item"""
    id: str = None
    item_uuid: UUID = uuid4()
    type: ResourceType = None
    stac_version: str = None
    stac_extensions: typing.List[str] = None
    geometry: typing.Optional[dict] = None
    bbox: typing.List[float] = None
    properties: ResourceProperties = None
    links: typing.List[ResourceLink] = None
    assets: typing.Dict[str, ResourceAsset] = None
    collection: str = None
    stac_object: STACObject = None


@dataclasses.dataclass
class ItemSearch:
    """ Definition for the pystac-client item search parameters"""
    ids: typing.Optional[list] = None
    page: typing.Optional[int] = 1
    page_size: typing.Optional[int] = 10
    collections: typing.Optional[list] = None
    datetime: typing.Optional[QtCore.QDateTime] = None
    spatial_extent: typing.Optional[QgsRectangle] = None
    start_datetime: typing.Optional[QtCore.QDateTime] = None
    end_datetime: typing.Optional[QtCore.QDateTime] = None
    filter_text: str = None
    filter_lang: FilterLang = FilterLang.CQL_JSON
    sortby: SortField = None
    sort_order: SortOrder = SortOrder.ASCENDING

    def params(self):
        """ Converts the class members into a dictionary that
        can be used in searching the STAC API items using the
        pystac-client library

        :returns: Dictionary of parameters
        :rtype: dict
        """
        spatial_extent_available = (self.spatial_extent and
                                    not self.spatial_extent.isNull()
                                    )
        bbox = [
            self.spatial_extent.xMinimum(),
            self.spatial_extent.yMinimum(),
            self.spatial_extent.xMaximum(),
            self.spatial_extent.yMaximum(),
        ] if spatial_extent_available else None

        datetime_str = None
        if self.start_datetime and not self.end_datetime:
            datetime_str = f"{self.start_datetime.toString(QtCore.Qt.ISODate)}"
        elif self.end_datetime and not self.start_datetime:
            datetime_str = f"{self.end_datetime.toString(QtCore.Qt.ISODate)}"
        elif self.start_datetime and self.end_datetime:
            datetime_str = f"{self.start_datetime.toString(QtCore.Qt.ISODate)}/" \
                           f"{self.end_datetime.toString(QtCore.Qt.ISODate)}"

        method = 'POST'
        text = None

        if self.filter_text:
            if self.filter_lang == FilterLang.CQL2_TEXT:
                method = 'GET'
                text = self.filter_text
            else:
                text = json.loads(self.filter_text)

        filter_lang_values = {
            FilterLang.CQL_JSON: 'cql-json',
            FilterLang.CQL2_JSON: 'cql2-json',
            FilterLang.CQL2_TEXT: 'cql2-text'
        }

        filter_lang_text = filter_lang_values[self.filter_lang] \
            if self.filter_lang else None

        filter_text = text \
            if self.filter_lang in \
               [FilterLang.CQL_JSON,
                FilterLang.CQL2_JSON,
                FilterLang.CQL2_TEXT
                ] else None

        query_text = text \
            if self.filter_lang == FilterLang.STAC_QUERY else None

        sort_lang_values = {
            SortField.ID: 'id',
            SortField.COLLECTION: 'collection',
        }

        field = sort_lang_values[self.sortby] if self.sortby else None

        order = 'asc' \
            if self.sort_order == SortOrder.ASCENDING else 'desc'

        sort_load = [
            {
                'field': field,
                'direction': order,
            }
        ] if self.sortby else []

        parameters = {
            "ids": self.ids,
            "collections": self.collections or None,
            "method": method,
            "limit": self.page_size,
            "bbox": bbox,
            "datetime": datetime_str,
            "filter_lang": filter_lang_text,
            "filter": filter_text,
            "query": query_text,
        }

        if self.sortby:
            parameters["sortby"] = sort_load

        return parameters


@dataclasses.dataclass
class SearchFilters:
    """ Stores search filters inputs"""
    page: typing.Optional[int] = 1
    page_size: typing.Optional[int] = 10
    collections: typing.Optional[list] = None
    start_date: typing.Optional[QtCore.QDateTime] = None
    end_date: typing.Optional[QtCore.QDateTime] = None
    spatial_extent: typing.Optional[QgsRectangle] = None
    date_filter: bool = False
    spatial_extent_filter: bool = False
    advanced_filter: bool = False
    filter_lang: FilterLang = FilterLang.CQL_TEXT
    filter_text: str = None
    sort_field: SortField = None
    sort_order: SortOrder = SortOrder.ASCENDING
