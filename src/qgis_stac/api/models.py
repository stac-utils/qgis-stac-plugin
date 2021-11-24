# -*- coding: utf-8 -*-
""" QGIS STAC plugin models

"""

import datetime
import enum
import typing
import dataclasses
from uuid import UUID

from qgis.core import QgsRectangle


@dataclasses.dataclass
class ResourcePagination:
    total_records: int
    current_page: int
    page_size: int


class GeometryType(enum.Enum):
    POINT = "Point"
    LINESTRING = "LineString"
    POLYGON = "Polygon"
    MULTIPOINT = "MultiPoint"
    MULTILINESTRING = "MultiLineString"
    MULTIPOLYGON = "MultiPolygon"


class ResourceType(enum.Enum):
    COLLECTION = "Collection"
    FEATURE = "Feature"
    CATALOG = "Catalog"


class SpatialExtent:
    bbox: typing.List[int]


class TemporalExtent:
    interval: typing.List[str]


class ResourceAsset:
    href: str
    title: str
    description: str
    type: str
    roles: typing.List[str]


class ResourceExtent:
    spatial: SpatialExtent
    temporal: TemporalExtent


class ResourceLink:
    href: str
    rel: str
    title: str
    type: str


class ResourceProperties:
    title: str
    description: str
    datetime: datetime.datetime
    created: datetime.datetime
    updated: datetime.datetime
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
    license: str


class ResourceProvider:
    name: str
    description: str
    roles: str
    urls: [str]


# TODO Update the geometry coordinates type to include
# all geometry types
class ResourceGeometry:
    type: GeometryType
    coordinates: typing.List[typing.List[int]]


class Catalog:
    id: int
    uuid: UUID
    title: str
    description: str
    type: ResourceType
    stac_version: str
    stac_extensions: typing.List[str]
    links: typing.List[ResourceLink]


class Collection:
    id: int
    uuid: UUID
    title: str
    description: str
    keywords: typing.List[str]
    license: str
    type: ResourceType
    stac_version: str
    stac_extensions: typing.List[str]
    links: typing.List[ResourceLink]
    assets: typing.Dict[str, ResourceAsset]
    providers: typing.List[ResourceProvider]
    extent: ResourceExtent
    summaries: typing.Dict[str, str]


class Item:
    id: int
    uuid: UUID
    type: ResourceType
    stac_version: str
    stac_extensions: typing.List[str]
    geometry: ResourceGeometry
    bbox: typing.List[float]
    properties: ResourceProperties
    links: typing.List[ResourceLink]
    assets: typing.Dict[str, ResourceAsset]
    collection: str


@dataclasses.dataclass
class ItemSearch:
    page: typing.Optional[int] = 1
    page_size: typing.Optional[int] = 10
    title: typing.Optional[str] = None
    collection: typing.Optional[str] = None
    spatial_extent: typing.Optional[QgsRectangle] = None
