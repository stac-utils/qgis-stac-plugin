# -*- coding: utf-8 -*-
""" QGIS STAC API plugin models

The STAC API related resources have been defined
in accordance to their definition available on
https://github.com/radiantearth/stac-api-spec/tree/master/stac-spec

"""

import datetime
import enum
import typing
import dataclasses
from uuid import UUID

from qgis.PyQt import (
    QtCore
)

from qgis.core import QgsRectangle


@dataclasses.dataclass
class ResourcePagination:
    """The plugin resource pagination for the search results"""
    total_records: int
    current_page: int
    page_size: int


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


class ResourceExtent:
    """The STAC API extent"""
    spatial: SpatialExtent
    temporal: TemporalExtent


class ResourceLink:
    """The STAC API extent"""
    href: str
    rel: str
    title: str
    type: str


class ResourceProperties:
    """Represents the STAC API Properties object,
    which contains additional metadata fields
    for the STAC API resources.
    """
    title: str
    description: str
    datetime: datetime.datetime
    created: datetime.datetime
    updated: datetime.datetime
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
    license: str


class ResourceProvider:
    """Represents the STAC API Provider object,
    which contains information about the provider that
    captured the content available on a STAC API collections.
    """
    name: str
    description: str
    roles: str
    urls: [str]


# TODO Update the geometry coordinates type to include
# all geometry types
class ResourceGeometry:
    """The GeoJSON geometry footprint STAC API assets"""
    type: GeometryType
    coordinates: typing.List[typing.List[int]]


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


class Collection:
    """ Represents the STAC API Collection"""
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
    """ Represents the STAC API Item"""
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
    """ Definition for the pystac-client item search parameters"""
    ids: typing.Optional[int] = 1
    page: typing.Optional[int] = 1
    page_size: typing.Optional[int] = 10
    collections: typing.Optional[str] = None
    datetime: typing.Optional[datetime.datetime] = None
    spatial_extent: typing.Optional[QgsRectangle] = None
    start_datetime: typing.Optional[QtCore.QDateTime] = None
    end_datetime: typing.Optional[QtCore.QDateTime] = None

    def params(self):
        """ Converts the class members into a dictionary that
        can be used in searching the STAC API items using the
        pystac-client library

        :returns: Dictionary of parameters
        :rtype: dict
        """
        bbox = [
            self.spatial_extent.xMinimum(),
            self.spatial_extent.yMinimum(),
            self.spatial_extent.xMaximum(),
            self.spatial_extent.yMaximum(),
        ]
        datetime_str = None
        if self.start_datetime and not self.start_datetime:
            datetime_str = f"{self.start_datetime.toString(QtCore.Qt.ISODate)}"
        elif self.end_datetime and not self.start_datetime:
            datetime_str = f"{self.end_datetime.toString(QtCore.Qt.ISODate)}"
        elif self.start_datetime and self.end_datetime:
            datetime_str = f"{self.start_datetime.toString(QtCore.Qt.ISODate)}\"" \
                       f"{self.end_datetime.toString(QtCore.Qt.ISODate)}"

        parameters = {
            "ids": self.ids,
            "collections": self.collections or None,
            "limit": self.page_size or None,
            "bbox": bbox or None,
            "datetime": datetime_str,
        }

        return parameters
