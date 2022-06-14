# -*- coding: utf-8 -*-
"""
    Handles storage and retrieval of the plugin QgsSettings.
"""

import contextlib
import dataclasses
import datetime
import enum
import typing
import uuid

from qgis.PyQt import (
    QtCore,
    QtWidgets,
)
from qgis.core import QgsRectangle, QgsSettings

from .api.models import (
    ApiCapability,
    Collection,
    Conformance,
    FilterLang,
    Item,
    ResourceAsset,
    ResourceExtent,
    ResourceLink,
    ResourceProvider,
    SearchFilters,
    SortField,
    SortOrder,
    SpatialExtent,
    TemporalExtent,
)


@contextlib.contextmanager
def qgis_settings(group_root: str, settings=None):
    """Context manager to help defining groups when creating QgsSettings.

    :param group_root: Name of the root group for the settings.
    :type group_root: str

    :param settings: QGIS settings to use
    :type settings: QgsSettings

    :yields: Instance of the created settings.
    :type: QgsSettings
    """
    if settings is None:
        settings = QgsSettings()
    settings.beginGroup(group_root)
    try:
        yield settings
    finally:
        settings.endGroup()


@dataclasses.dataclass
class ConnectionSettings:
    """Manages the plugin connection settings.
    """

    id: uuid.UUID
    name: str
    url: str
    page_size: int
    collections: list
    conformances: list
    search_items: list
    capability: ApiCapability
    sas_subscription_key: str
    created_date: datetime.datetime = datetime.datetime.now()
    auth_config: typing.Optional[str] = None

    @classmethod
    def from_qgs_settings(
            cls,
            identifier: str,
            settings: QgsSettings):
        """Reads QGIS settings and parses them into a connection
        settings instance with the respective settings values as properties.

        :param identifier: Connection identifier
        :type identifier: str

        :param settings: QGIS settings.
        :type settings: QgsSettings

        :returns: Connection settings object
        :rtype: ConnectionSettings
        """
        collections = []
        conformances = []
        auth_cfg = None
        capability = None
        try:
            collections = settings_manager.get_collections(
                uuid.UUID(identifier)
            )
            conformances = settings_manager.get_conformances(
                uuid.UUID(identifier)
            )
            items = settings_manager.get_items(
                uuid.UUID(identifier)
            )
            capability_value = settings.value("capability", defaultValue=None)
            capability = ApiCapability(capability_value) \
                if capability_value else None
            created_date = datetime.datetime.strptime(
                settings.value("created_date"),
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ) if settings.value("created_date") is not None else None
            auth_cfg = settings.value("auth_config").strip()
        except AttributeError:
            created_date = datetime.datetime.now()

        return cls(
            id=uuid.UUID(identifier),
            name=settings.value("name"),
            url=settings.value("url"),
            page_size=int(settings.value("page_size", defaultValue=10)),
            collections=collections,
            conformances=conformances,
            capability=capability,
            sas_subscription_key=settings.value("sas_subscription_key"),
            created_date=created_date,
            auth_config=auth_cfg,
            search_items=items,
        )


@dataclasses.dataclass
class CollectionSettings(Collection):
    """Plugin STAC API collection setting
    """

    @classmethod
    def from_qgs_settings(
            cls,
            identifier: str,
            settings: QgsSettings):
        """Reads QGIS settings and parses them into a collection
        settings instance with the respective settings values as properties.

        :param identifier: Collection identifier
        :type identifier: str

        :param settings: QGIS settings.
        :type settings: QgsSettings

        :returns: Collection settings object
        :rtype: CollectionSettings
        """

        return cls(
            uuid=uuid.UUID(identifier),
            title=settings.value("title", None),
            id=settings.value("id", None),
        )

    @classmethod
    def get_collection_links(cls, collection_settings):
        """ Fetches links from the passed collection settings and
        returns a list of resource links.

        :param collection_settings: Collection settings instance
        :type collection_settings: CollectionSettings

        :returns: Resource links list
        :rtype: list
        """
        links = []
        key = "links"

        with qgis_settings(key, collection_settings) as settings:

            title = settings.value("title", None)
            href = settings.value("href", None)
            rel = settings.value("rel", None)
            type = settings.value("type", None)

            link = ResourceLink(
                title=title,
                href=href,
                rel=rel,
                type=type,
            )
            links.append(link)
        return links

    @classmethod
    def get_collection_extent(cls, collection_settings):
        """ Fetches STAC collection extent from
         the passed collection settings.

        :param collection_settings: Collection settings instance
        :type collection_settings: CollectionSettings

        :returns: Extent instance that contain temporal and spatial extent
        :rtype: ResourceExtent
        """
        spatial_key = "extent/spatial"
        temporal_key = "extent/temporal"

        with qgis_settings(spatial_key, collection_settings) as settings:
            bbox = settings.value("bbox", None)
            spatial = SpatialExtent(bbox=bbox)
        with qgis_settings(temporal_key, collection_settings) as settings:
            temporal = TemporalExtent(interval=settings.value("interval", None))

        extent = ResourceExtent(spatial=spatial, temporal=temporal)

        return extent

    @classmethod
    def get_collection_providers(cls, collection_settings):
        """ Fetches providers instances from the passed
        collection settings and
        returns a list of resource links.

        :param collection_settings: Collection settings instance
        :type collection_settings: CollectionSettings

        :returns: Resource provider list
        :rtype: list
        """
        providers = []

        with qgis_settings("providers", collection_settings) as settings:

            name = settings.value("name", None)
            description = settings.value("description", None)
            roles = settings.value("roles", None)
            url = settings.value("url", None)
            provider = ResourceProvider(
                name=name,
                description=description,
                roles=roles,
                url=url
            )
            providers.append(provider)
        return providers


@dataclasses.dataclass
class ConformanceSettings(Conformance):
    """Plugin STAC API conformance setting
    """

    @classmethod
    def from_qgs_settings(
            cls,
            identifier: str,
            settings: QgsSettings):
        """Reads QGIS settings and parses them into a conformance
        settings instance with the respective settings values as properties.

        :param identifier: Conformance identifier
        :type identifier: str

        :param settings: QGIS settings.
        :type settings: QgsSettings

        :returns: Conformance settings object
        :rtype: ConformanceSettings
        """
        return cls(
            id=uuid.UUID(identifier),
            name=settings.value("name"),
            uri=settings.value("uri")
        )


class Settings(enum.Enum):
    """ Plugin settings names"""
    AUTO_ASSET_LOADING = "auto_asset_loading"
    DOWNLOAD_FOLDER = "download_folder"
    REFRESH_FREQUENCY = "refresh/period"
    REFRESH_FREQUENCY_UNIT = "refresh/unit"
    REFRESH_LAST_UPDATE = "refresh/last_update"
    REFRESH_STATE = "refresh/state"


@dataclasses.dataclass
class ItemSettings(Item):
    """Plugin STAC API Item settings class
    """

    @classmethod
    def from_qgs_settings(
            cls,
            identifier: str,
            settings: QgsSettings):
        """Reads QGIS settings and parses them into the item
        settings instance with the respective settings values as properties.

        :param identifier: Item identifier
        :type identifier: str

        :param settings: QGIS settings.
        :type settings: QgsSettings

        :returns: Conformance settings object
        :rtype: ConformanceSettings
        """
        assets = cls.get_assets(settings)
        item_uuid = None
        try:
            item_uuid = uuid.UUID(identifier)
        except:
            pass
        return cls(
            item_uuid=item_uuid,
            id=settings.value("id"),
            stac_version=settings.value("stac_version"),
            assets=assets,
            stac_object=settings.value("stac_object")
        )

    @classmethod
    def get_assets(cls, item_settings):
        """Gets the store item assets from the given settings.

        :param name: Plugin item settings
        :type name: QgsSettings()

        :returns: Plugin STAC Item assets list
        :rtype: []
        """
        assets = []
        key = "assets"

        with qgis_settings(key, item_settings) as settings:

            title = settings.value("title", None)
            href = settings.value("href", None)
            description = settings.value("description", None)
            roles = settings.value("roles", None)
            type = settings.value("type", None)

            asset = ResourceAsset(
                title=title,
                href=href,
                roles=roles,
                type=type,
                description=description,
            )
            assets.append(asset)
        return assets


class SettingsManager(QtCore.QObject):
    """Manages saving/loading settings for the plugin in QgsSettings.
    """

    BASE_GROUP_NAME: str = "qgis_stac"
    CONNECTION_GROUP_NAME: str = "connections"
    SELECTED_CONNECTION_KEY: str = "selected_connection"
    COLLECTION_GROUP_NAME: str = "collections"
    CONFORMANCE_GROUP_NAME: str = "conformance"
    ITEMS_GROUP_NAME: str = "items"
    ASSETS_GROUP_NAME: str = "assets"

    settings = QgsSettings()

    connections_settings_updated = QtCore.pyqtSignal()

    def set_value(self, name: str, value):
        """Adds a new setting key and value on the plugin specific settings.

        :param name: Name of setting key
        :type name: str

        :param value: Value of the setting
        :type value: Any

        """
        self.settings.setValue(
            f"{self.BASE_GROUP_NAME}/{name}",
            value
        )

    def get_value(
            self,
            name: str,
            default=None,
            setting_type=None):
        """Gets value of the setting with the passed name.

        :param name: Name of the setting key
        :type name: str

        :param default: Default value returned when the
         setting key does not exists
        :type default: Any

        :param setting_type: Type of the store setting
        :type setting_type: Any

        :returns: Value of the setting
        :rtype: Any
        """
        if setting_type:
            return self.settings.value(
                f"{self.BASE_GROUP_NAME}/{name}",
                default,
                setting_type
            )
        return self.settings.value(
            f"{self.BASE_GROUP_NAME}/{name}",
            default
        )

    def remove(self, name):
        """Remove the setting with the specified name.

        :param name: Name of the setting key
        :type name: str
        """
        self.settings.remove(
            f"{self.BASE_GROUP_NAME}/{name}"
        )

    def list_connections(self) -> typing.List[ConnectionSettings]:
        """Lists all the plugin connections stored in the QgsSettings.

        :return: Plugin connections
        :rtype: List[ConnectionSettings]
        """
        result = []
        with qgis_settings(
                f"{self.BASE_GROUP_NAME}/"
                f"{self.CONNECTION_GROUP_NAME}") \
                as settings:
            for connection_id in settings.childGroups():
                connection_settings_key = self._get_connection_settings_base(
                    connection_id
                )
                with qgis_settings(connection_settings_key) \
                        as connection_settings:
                    result.append(
                        ConnectionSettings.from_qgs_settings(
                            connection_id, connection_settings
                        )
                    )
        return result

    def delete_all_connections(self):
        """Deletes all the plugin connections settings in QgsSettings.
        """
        with qgis_settings(
                f"{self.BASE_GROUP_NAME}"
                f"/{self.CONNECTION_GROUP_NAME}") \
                as settings:
            for connection_name in settings.childGroups():
                settings.remove(connection_name)
        self.clear_current_connection()
        self.connections_settings_updated.emit()

    def find_connection_by_name(self, name):
        """Finds a connection setting inside the plugin QgsSettings by name.

        :param name: Name of the connection
        :type: str

        :returns: Connection settings instance
        :rtype: ConnectionSettings
        """
        with qgis_settings(
                f"{self.BASE_GROUP_NAME}/"
                f"{self.CONNECTION_GROUP_NAME}") \
                as settings:
            for connection_id in settings.childGroups():
                connection_settings_key = self._get_connection_settings_base(
                    connection_id
                )
                with qgis_settings(connection_settings_key) \
                        as connection_settings:
                    connection_name = connection_settings.value("name")
                    if connection_name == name:
                        found_id = uuid.UUID(connection_id)
                        break
            else:
                raise ValueError(
                    f"Could not find a connection named "
                    f"{name!r} in QgsSettings"
                )
        return self.get_connection_settings(found_id)

    def get_connection_settings(
            self,
            identifier: uuid.UUID) -> ConnectionSettings:
        """Gets the connection setting with the specified identifier.

        :param identifier: Connection identifier
        :type identifier: uuid.UUID

        :returns: Connection settings instance
        :rtype: ConnectionSettings
        """
        settings_key = self._get_connection_settings_base(identifier)
        with qgis_settings(settings_key) as settings:
            connection_settings = ConnectionSettings.from_qgs_settings(
                str(identifier), settings
            )
        return connection_settings

    def save_connection_settings(
            self,
            connection_settings: ConnectionSettings):
        """Saves connection settings from the given connection object.

        :param connection_settings: Connection settings object
        :type connection_settings: ConnectionSettings

        """
        settings_key = self._get_connection_settings_base(
            connection_settings.id
        )
        created_date = connection_settings.created_date.\
            strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        capability = connection_settings.capability.value \
            if connection_settings.capability else None
        if connection_settings.conformances:
            for conformance in connection_settings.conformances:
                self.save_conformance(
                    connection_settings,
                    conformance
                )
        with qgis_settings(settings_key) as settings:
            settings.setValue("name", connection_settings.name)
            settings.setValue("url", connection_settings.url)
            settings.setValue("page_size", connection_settings.page_size)
            settings.setValue("capability", capability)
            settings.setValue(
                "sas_subscription_key",
                connection_settings.sas_subscription_key
            )
            settings.setValue("created_date", created_date)
            settings.setValue("auth_config", connection_settings.auth_config)
        self.connections_settings_updated.emit()

    def delete_connection(self, identifier: uuid.UUID):
        """Deletes plugin connection that match the passed identifier.

        :param identifier: Connection identifier
        :type identifier: uuid.UUID
        """
        if self.is_current_connection(identifier):
            self.clear_current_connection()
        with qgis_settings(
                f"{self.BASE_GROUP_NAME}/"
                f"{self.CONNECTION_GROUP_NAME}")\
                as settings:
            settings.remove(str(identifier))
        self.connections_settings_updated.emit()

    def get_current_connection(self) -> typing.Optional[ConnectionSettings]:
        """Gets the current active connection from the QgsSettings.

        :returns Connection settings instance
        :rtype ConnectionSettings

        """
        with qgis_settings(self.BASE_GROUP_NAME) as settings:
            current = settings.value(self.SELECTED_CONNECTION_KEY)
        if current is not None:
            result = self.get_connection_settings(uuid.UUID(current))
        else:
            result = None
        return result

    def get_latest_connection(self) -> typing.Optional[ConnectionSettings]:
        """Gets the most recent added connection from the QgsSettings.

        :returns Connection settings instance
        :rtype ConnectionSettings

        """
        connection_list = self.list_connections()
        if len(connection_list) < 1:
            return None
        latest_connection = connection_list[0]

        for connection in connection_list:
            if connection.created_date > latest_connection.created_date:
                latest_connection = connection

        return latest_connection

    def set_current_connection(self, identifier: uuid.UUID):
        """Updates the plugin settings and set the connection with the
           passed identifier as the selected connection.

        :param identifier: Connection identifier
        :type identifier: uuid.UUID
        """
        if identifier not in [conn.id for conn in self.list_connections()]:
            raise ValueError(f"Invalid connection identifier: {id!r}")
        serialized_id = str(identifier)
        with qgis_settings(self.BASE_GROUP_NAME) as settings:
            settings.setValue(self.SELECTED_CONNECTION_KEY, serialized_id)
        self.connections_settings_updated.emit()

    def clear_current_connection(self):
        """Removes the current selected connection in the settings.
        """
        with qgis_settings(self.BASE_GROUP_NAME) as settings:
            settings.setValue(self.SELECTED_CONNECTION_KEY, None)
        self.connections_settings_updated.emit()

    def is_current_connection(self, identifier: uuid.UUID):
        """Checks if the connection with the passed identifier
            is the current selected connection.

        :param identifier: Connection settings identifier.
        :type identifier: uuid.UUID
        """
        current = self.get_current_connection()
        return False if current is None else current.id == identifier

    def is_connection(self, identifier: uuid.UUID):
        """Checks if the connection with the identifier exists

        :param identifier: Connection settings identifier.
        :type identifier: uuid.UUID
        """
        connections = self.list_connections()
        exists = any([connection.id == identifier for connection in connections])
        return exists

    def _get_connection_settings_base(
            self,
            identifier: typing.Union[str, uuid.UUID]):
        """Gets the connection settings base url.

        :param identifier: Connection settings identifier
        :type identifier: uuid.UUID

        :returns Connection settings base group
        :rtype str
        """
        return f"{self.BASE_GROUP_NAME}/" \
               f"{self.CONNECTION_GROUP_NAME}/" \
               f"{str(identifier)}"

    def _get_collection_settings_base(
            self,
            connection_identifier,
            identifier
    ):
        """Gets the collection settings base url.

        :param connection_identifier: Connection settings identifier
        :type connection_identifier: uuid.UUID

        :param identifier: Collection settings identifier
        :type identifier: uuid.UUID

        :returns Collection settings base group
        :rtype str
        """
        return f"{self.BASE_GROUP_NAME}/" \
               f"{self.CONNECTION_GROUP_NAME}/" \
               f"{str(connection_identifier)}/" \
               f"{self.COLLECTION_GROUP_NAME}/" \
               f"{str(identifier)}"

    def _get_conformance_settings_base(
            self,
            connection_identifier,
            identifier
    ):
        """Gets the conformance settings base url.

        :param connection_identifier: Connection settings identifier
        :type connection_identifier: uuid.UUID

        :param identifier: Conformance settings identifier
        :type identifier: uuid.UUID

        :returns Conformance settings base group
        :rtype str
        """
        return f"{self.BASE_GROUP_NAME}/" \
               f"{self.CONNECTION_GROUP_NAME}/" \
               f"{str(connection_identifier)}/" \
               f"{self.CONFORMANCE_GROUP_NAME}/" \
               f"{str(identifier)}"

    def _get_item_settings_base(
            self,
            connection_identifier,
            page,
            identifier
    ):
        """Gets the items settings base group.

        :param connection_identifier: Connection settings identifier
        :type connection_identifier: uuid.UUID

        :param page: The result page that the item was when fetched.
        :type page: str

        :param identifier: The item settings identifier
        :type identifier: uuid.UUID

        :returns Items settings base group
        :rtype str
        """
        return f"{self.BASE_GROUP_NAME}/" \
               f"{self.CONNECTION_GROUP_NAME}/" \
               f"{connection_identifier}/" \
               f"{self.ITEMS_GROUP_NAME}/" \
               f"{page}/" \
               f"{identifier}"

    def save_collection(self, connection, collection_settings):
        """ Save the passed colection settings into the plugin settings

        :param connection: Connection settings
        :type connection:  CollectionSettings

        :param collection_settings: Collection settings
        :type collection_settings:  CollectionSettings
        """
        settings_key = self._get_collection_settings_base(
            connection.id,
            collection_settings.uuid
        )

        with qgis_settings(settings_key) as settings:
            settings.setValue("title", collection_settings.title)
            settings.setValue("id", collection_settings.id)

    def save_collection_links(self, links, key):
        """ Saves the collection links into plugin settings
        using the provided settings group key.

        :param links: List of collection links
        :type links: []

        :param key: QgsSettings group key.
        :type key: str
        """
        for link in links or []:
            link_uuid = uuid.uuid4()
            settings_key = f"{key}/links/{link_uuid}"
            with qgis_settings(settings_key) as settings:
                settings.setValue("title", link.title)
                settings.setValue("href", link.href)
                settings.setValue("rel", link.rel)
                settings.setValue("type", link.type)

    def save_collection_providers(self, providers, key):
        """ Saves the collection provider into plugin settings
        using the provided settings group key.

        :param links: List of collection providers
        :type links: []

        :param key: QgsSettings group key.
        :type key: str
        """
        for provider in providers or []:
            provider_uuid = uuid.uuid4()
            settings_key = f"{key}/links/{provider_uuid}"
            with qgis_settings(settings_key) as settings:
                settings.setValue("name", provider.name)
                settings.setValue("description", provider.description)
                settings.setValue("role", provider.role)
                settings.setValue("url", provider.url)

    def save_collection_extent(self, extent, key):
        """ Saves the collection extent into plugin settings
        using the provided settings group key.

        :param links: Collection extent
        :type links: models.Extent

        :param key: QgsSettings group key.
        :type key: str
        """
        interval = extent.temporal.interval
        spatial_extent = extent.spatial.bbox

        spatial_key = f"{key}/extent/spatial/"
        with qgis_settings(spatial_key) as settings:
            settings.setValue("bbox", spatial_extent)

        temporal_key = f"{key}/extent/temporal/"
        with qgis_settings(temporal_key) as settings:
            settings.setValue("interval", interval)

    def save_items(self, connection, items, page):
        """ Save the passed items into the plugin connection settings

        :param connection: Connection settings
        :type connection:  ConnectionSettings
        """
        for item in items:
            item_setting = ItemSettings(
                item_uuid=item.item_uuid,
                id=item.id,
                assets=item.assets,
                stac_object=item.stac_object
            )
            self.save_item(connection, item_setting, page)

    def save_item(self, connection, item_settings, page):
        """ Save the passed item settings into the plugin settings

        :param connection: Connection settings
        :type connection:  ConnectionSettings
        """
        settings_key = self._get_item_settings_base(
            connection.id,
            page,
            item_settings.item_uuid
        )

        with qgis_settings(settings_key) as settings:
            settings.setValue("id", item_settings.id)
            settings.setValue("item_uuid", item_settings.item_uuid)
            settings.setValue("stac_version", item_settings.stac_version)
            settings.setValue("stac_object", item_settings.stac_object)
        self.save_item_assets(item_settings.assets, settings_key)

    def save_item_assets(self, assets, key):
        """ Saves the collection provider into plugin settings
        using the provided settings group key.

        :param links: List of collection providers
        :type links: []

        :param key: QgsSettings group key.
        :type key: str
        """
        for asset in assets or []:
            asset_uuid = uuid.uuid4()
            settings_key = f"{key}/{self.ASSETS_GROUP_NAME}/{asset_uuid}"
            with qgis_settings(settings_key) as settings:
                settings.setValue("title", asset.title)
                settings.setValue("description", asset.description)
                settings.setValue("href", asset.href)
                settings.setValue("roles", asset.roles)
                settings.setValue("type", asset.type)

    def get_collection(self, identifier, connection):
        """ Retrieves the collection that matches the passed identifier.

        :param identifier: Collection identifier
        :type identifier: str

        :param connection: Connection that the collection belongs to.
        :type connection: ConnectionSettings

        :returns Collection settings instance
        :rtype CollectionSettings
        """

        settings_key = self._get_collection_settings_base(
            connection.id,
            identifier
        )
        with qgis_settings(settings_key) as settings:
            collection_settings = CollectionSettings.from_qgs_settings(
                str(identifier), settings
            )
        return collection_settings

    def get_collection(self, collection_id, connection):
        """ Retrieves the first collection that matched the passed collection id.

        :param collection_id: STAC collection id
        :type collection_id: str

        :param connection: Connection that the collection belongs to.
        :type connection: ConnectionSettings

        :returns Collection settings instance
        :rtype CollectionSettings
        """

        connection_identifier = connection.id

        result = []
        with qgis_settings(
                f"{self.BASE_GROUP_NAME}/"
                f"{self.CONNECTION_GROUP_NAME}/"
                f"{str(connection_identifier)}/"
                f"{self.COLLECTION_GROUP_NAME}"
        ) \
                as settings:
            for uuid in settings.childGroups():
                collection_settings_key = self._get_collection_settings_base(
                    connection_identifier,
                    uuid
                )
                with qgis_settings(collection_settings_key) \
                        as collection_settings:
                    collection = CollectionSettings.from_qgs_settings(
                            uuid, collection_settings
                    )
                    if collection.id == collection_id:
                        return collection
        return None

    def get_collections(self, connection_identifier):
        """ Gets all the available collections settings in the
        provided connection

        :param connection_identifier: Connection identifier from which
        to get all the available collections
        :type connection_identifier: uuid.UUID

        :returns List of the collection settings instances
        :rtype list
        """
        result = []
        with qgis_settings(
                f"{self.BASE_GROUP_NAME}/"
                f"{self.CONNECTION_GROUP_NAME}/"
                f"{str(connection_identifier)}/"
                f"{self.COLLECTION_GROUP_NAME}"
        ) \
                as settings:
            for uuid in settings.childGroups():
                collection_settings_key = self._get_collection_settings_base(
                    connection_identifier,
                    uuid
                )
                with qgis_settings(collection_settings_key) \
                        as collection_settings:
                    result.append(
                        CollectionSettings.from_qgs_settings(
                            uuid, collection_settings
                        )
                    )
        return result

    def delete_all_collections(self, connection):
        """Deletes all the plugin connections collections settings,
        in the connection.

        :param connection: Connection from which to delete all the
        available collections
        :type connection: ConnectionSettings
        """
        with qgis_settings(
                f"{self.BASE_GROUP_NAME}/" \
                f"{self.CONNECTION_GROUP_NAME}/" \
                f"{str(connection.id)}/"\
                f"{self.COLLECTION_GROUP_NAME}"
        ) \
                as settings:
            for collection_name in settings.childGroups():
                settings.remove(collection_name)

    def get_conformances(self, connection_identifier):
        """ Gets all the available conformances settings in the
        provided connection

        :param connection_identifier: Connection identifier from which
        to get all the available collections
        :type connection_identifier: uuid.UUID

        :returns List of the conformances settings instances
        :rtype list
        """
        result = []
        with qgis_settings(
                f"{self.BASE_GROUP_NAME}/"
                f"{self.CONNECTION_GROUP_NAME}/"
                f"{str(connection_identifier)}/"
                f"{self.CONFORMANCE_GROUP_NAME}"
        ) \
                as settings:
            for conformance_id in settings.childGroups():
                conformance_settings_key = self._get_conformance_settings_base(
                    connection_identifier,
                    conformance_id
                )
                with qgis_settings(conformance_settings_key) \
                        as conformance_settings:
                    result.append(
                        ConformanceSettings.from_qgs_settings(
                            conformance_id,
                            conformance_settings
                        )
                    )
        return result

    def save_conformance(self, connection, conformance_settings):
        """ Save the passed conformance settings into the plugin settings

        :param connection: Connection settings
        :type connection:  CollectionSettings

        :param conformance_settings: Conformance settings
        :type conformance_settings:  ConformanceSettings
        """
        settings_key = self._get_conformance_settings_base(
            connection.id,
            conformance_settings.id
        )

        with qgis_settings(settings_key) as settings:
            settings.setValue("name", conformance_settings.name)
            settings.setValue("uri", conformance_settings.uri)

    def delete_all_conformance(self, connection):
        """Deletes all the connection conformance settings,
        in the connection.

        :param connection: Connection from which to delete all the
        available conformance
        :type connection: ConnectionSettings
        """
        with qgis_settings(
                f"{self.BASE_GROUP_NAME}/" \
                f"{self.CONNECTION_GROUP_NAME}/" \
                f"{str(connection.id)}/"\
                f"{self.CONFORMANCE_GROUP_NAME}"
        ) \
                as settings:
            for conformance_name in settings.childGroups():
                settings.remove(conformance_name)

    def get_items(self, connection_identifier, items_uuids=None):
        """ Gets all the available items settings in the
        provided connection.

        :param connection_identifier: Connection identifier from which
        to get all the available collections
        :type connection_identifier: uuid.UUID

        :param items_uuids: List of target items ids
        :type items_uuids: []

        :returns List of the item settings instances
        :rtype list
        """
        result = {}
        with qgis_settings(
                f"{self.BASE_GROUP_NAME}/"
                f"{self.CONNECTION_GROUP_NAME}/"
                f"{str(connection_identifier)}/"
                f"{self.ITEMS_GROUP_NAME}"
        ) \
                as settings:
            for page in settings.childGroups():
                with qgis_settings(
                        f"{self.BASE_GROUP_NAME}/"
                        f"{self.CONNECTION_GROUP_NAME}/"
                        f"{str(connection_identifier)}/"
                        f"{self.ITEMS_GROUP_NAME}/"
                        f"{page}"
                ) as page_settings:
                    result[f"{page}"] = []
                    for item_id in page_settings.childGroups():
                        if items_uuids and item_id not in items_uuids:
                            continue
                        item_setting_key = self._get_item_settings_base(
                            connection_identifier,
                            page,
                            item_id
                        )
                        with qgis_settings(item_setting_key) \
                                as item_settings:
                            result[f"{page}"].append(
                                ItemSettings.from_qgs_settings(
                                    item_id,
                                    item_settings
                                )
                            )
        return result

    def delete_all_items(self, connection, page=None):
        """Deletes all the plugin connections items settings,
        in the connection.

        :param connection: Connection from which to delete all the
        available collections
        :type connection: ConnectionSettings
        """
        key = f"{self.BASE_GROUP_NAME}/" \
              f"{self.CONNECTION_GROUP_NAME}/" \
              f"{str(connection.id)}/" \
              f"{self.ITEMS_GROUP_NAME}"

        if page:
            key = f"{key}/{page}"

        with qgis_settings(key) as settings:
            for item_name in settings.childGroups():
                settings.remove(item_name)

    def save_search_filters(
        self,
        filters
    ):
        """ Save the search filters into the plugin settings

        :param filters: Search filters
        :type filters: SearchFilters
        """
        with qgis_settings(
            f"{self.BASE_GROUP_NAME}/search_filters"
        ) as settings:
            if filters.start_date is not None:
                settings.setValue(
                    "start_date",
                    filters.start_date.toString(QtCore.Qt.ISODate),
                )
            else:
                settings.setValue("start_date", None)
            if filters.end_date is not None:
                settings.setValue(
                    "end_date",
                    filters.end_date.toString(QtCore.Qt.ISODate),
                )
            else:
                settings.setValue("end_date", None)
            if filters.spatial_extent is not None:
                settings.setValue(
                    "spatial_extent_north",
                    filters.spatial_extent.yMaximum()
                )
                settings.setValue(
                    "spatial_extent_south",
                    filters.spatial_extent.yMinimum()
                )
                settings.setValue(
                    "spatial_extent_east",
                    filters.spatial_extent.xMaximum()
                )
                settings.setValue(
                    "spatial_extent_west",
                    filters.spatial_extent.xMinimum()
                )
            settings.setValue("date_filter", filters.date_filter)
            settings.setValue("extent_filter", filters.spatial_extent_filter)
            settings.setValue("advanced_filter", filters.advanced_filter)
            settings.setValue("filter_lang", filters.filter_lang.name) \
                if filters.filter_lang else None
            settings.setValue("filter_text", filters.filter_text)

            sort_field = filters.sort_field.name if filters.sort_field else None
            settings.setValue("sort_field", sort_field)

            settings.setValue("sort_order", filters.sort_order.name) \
                if filters.sort_order else None
        current_connection = self.get_current_connection()
        if filters.collections:
            self.delete_all_collections(current_connection)
            for collection in filters.collections:
                collection = CollectionSettings(
                    uuid=uuid.uuid4(),
                    id=collection.id,
                    title=collection.title
                )
                self.save_collection(
                    current_connection,
                    collection
                )

    def get_search_filters(self):
        """ Retrieve the store fitlers settings"""
        current_connection = self.get_current_connection()
        with qgis_settings(
            f"{self.BASE_GROUP_NAME}/search_filters"
        ) as settings:
            start_date = None
            end_date = None
            spatial_extent = None

            collections_settings = self.get_collections(current_connection.id) \
                if current_connection is not None else []
            collections = []

            for collection in collections_settings:
                collection_instance = Collection(
                    id=collection.id,
                    title=collection.title
                )
                collections.append(collection_instance)

            if settings.value("start_date"):
                start_date = QtCore.QDateTime.fromString(
                    settings.value("start_date"), QtCore.Qt.ISODate
                )
            if settings.value("end_date"):
                end_date = QtCore.QDateTime.fromString(
                    settings.value("end_date"), QtCore.Qt.ISODate
                )
            if settings.value("spatial_extent_north") is not None:
                spatial_extent = QgsRectangle(
                    float(settings.value("spatial_extent_east")),
                    float(settings.value("spatial_extent_south")),
                    float(settings.value("spatial_extent_west")),
                    float(settings.value("spatial_extent_north")),
                )
            date_filter = settings.value("date_filter", False, type=bool)
            extent_filter = settings.value("extent_filter", False, type=bool)

            advanced_filter = settings.value("advanced_filter", False, type=bool)

            filter_lang = FilterLang(settings.value("filter_lang", None)) \
                if settings.value("filter_lang", None) else None
            filter_text = settings.value("filter_text")

            sort_field = SortField(settings.value("sort_field", None)) \
                if settings.value("sort_field", None) else None

            sort_order = SortOrder(settings.value("sort_order", None)) \
                if settings.value("sort_order", None) else None

            return SearchFilters(
                collections=collections,
                start_date=start_date,
                end_date=end_date,
                spatial_extent=spatial_extent,
                date_filter=date_filter,
                spatial_extent_filter=extent_filter,
                advanced_filter=advanced_filter,
                filter_text=filter_text,
                filter_lang=filter_lang,
                sort_field=sort_field,
                sort_order=sort_order,
            )


settings_manager = SettingsManager()
