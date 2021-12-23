# -*- coding: utf-8 -*-
"""
    Handles storage and retrieval of the plugin QgsSettings.
"""

import contextlib
import dataclasses
import typing
import uuid
import datetime

from qgis.PyQt import (
    QtCore,
    QtWidgets,
)
from qgis.core import QgsRectangle, QgsSettings

from .api.models import (
    ApiCapability,
    SearchFilters
)


@contextlib.contextmanager
def qgis_settings(group_root: str):
    """Context manager to help defining groups when creating QgsSettings.

    :param group_root: Name of the root group for the settings.
    :type group_root: str

    :yields: Instance of the created settings.
    :type: QgsSettings
    """
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
    capability: ApiCapability
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
        auth_cfg = None
        capability = None
        try:

            auth_cfg = settings.value("auth_config").strip()
            collections = settings_manager.get_collections(
                uuid.UUID(identifier)
            )
            capability_value = settings.value("capability", defaultValue=None)
            capability = ApiCapability(capability_value) \
                if capability_value else None
            created_date = datetime.datetime.strptime(
                settings.value("created_date"),
                "%Y-%m-%dT%H:%M:%S.%fZ"
            )
        except AttributeError:
            created_date = datetime.datetime.now()

        return cls(
            id=uuid.UUID(identifier),
            name=settings.value("name"),
            url=settings.value("url"),
            page_size=int(settings.value("page_size", defaultValue=10)),
            collections=collections,
            capability=capability,
            created_date=created_date,
            auth_config=auth_cfg,
        )


@dataclasses.dataclass
class CollectionSettings:
    """Plugin STAC API collection setting
    """

    collection_id: uuid.UUID
    title: str
    id: str

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
            collection_id=uuid.UUID(identifier),
            title=settings.value("title"),
            id=settings.value("id")
        )


class SettingsManager(QtCore.QObject):
    """Manages saving/loading settings for the plugin in QgsSettings.
    """

    BASE_GROUP_NAME: str = "qgis_stac"
    CONNECTION_GROUP_NAME: str = "connections"
    SELECTED_CONNECTION_KEY: str = "selected_connection"
    COLLECTION_GROUP_NAME: str = "collections"

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
        with qgis_settings(settings_key) as settings:
            settings.setValue("name", connection_settings.name)
            settings.setValue("url", connection_settings.url)
            settings.setValue("page_size", connection_settings.page_size)
            settings.setValue("capability", capability)
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
        """
        return f"{self.BASE_GROUP_NAME}/" \
               f"{self.CONNECTION_GROUP_NAME}/" \
               f"{str(connection_identifier)}/" \
               f"{self.COLLECTION_GROUP_NAME}/" \
               f"{str(identifier)}"

    def save_collection(self, connection, collection_settings):
        """ Save the passed colection settings into the plugin settings

        :param connection: Connection settings
        :type connection:  CollectionSettings

        :param collection_settings: Collection settings
        :type collection_settings:  CollectionSettings
        """
        settings_key = self._get_collection_settings_base(
            connection.id,
            collection_settings.collection_id
        )

        with qgis_settings(settings_key) as settings:
            settings.setValue("title", collection_settings.title)
            settings.setValue("id", collection_settings.id)

    def get_collection(self, identifier, connection):
        """ Retrieves the collection with the identifier

        :param identifier: Collection identifier
        :type identifier: str

        :param connection: Connection that the collection belongs to.
        :type connection: str
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

    def get_collections(self, connection_identifier):
        """ Gets all the available collections settings in the
        provided connection

        :param connection_identifier: Connection identifier from which
        to get all the available collections
        :type connection_identifier: uuid.UUID
        """
        result = []
        with qgis_settings(
                f"{self.BASE_GROUP_NAME}/"
                f"{self.CONNECTION_GROUP_NAME}/"
                f"{str(connection_identifier)}/"
                f"{self.COLLECTION_GROUP_NAME}"
        ) \
                as settings:
            for collection_id in settings.childGroups():
                collection_settings_key = self._get_collection_settings_base(
                    connection_identifier,
                    collection_id
                )
                with qgis_settings(collection_settings_key) \
                        as collection_settings:
                    result.append(
                        CollectionSettings.from_qgs_settings(
                            collection_id, collection_settings
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
        current_connection = self.get_current_connection()
        if filters.collections:
            self.delete_all_collections(current_connection)
        for collection in filters.collections:
            collection = CollectionSettings(
                collection_id=uuid.uuid4(),
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

            collections = self.get_collections(current_connection.id) \
                if current_connection is not None else []

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

            return SearchFilters(
                collections=collections,
                start_date=start_date,
                end_date=end_date,
                spatial_extent=spatial_extent,
                date_filter=date_filter,
                spatial_extent_filter=extent_filter,
            )


settings_manager = SettingsManager()
