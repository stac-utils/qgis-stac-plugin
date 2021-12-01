# -*- coding: utf-8 -*-
"""
    Handles storage and retrieval of the plugin QgsSettings.
"""

import contextlib
import dataclasses
import typing
import uuid

from qgis.PyQt import (
    QtCore,
    QtWidgets,
)
from qgis.core import QgsRectangle, QgsSettings


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
        try:
            auth_cfg = settings.value("auth_config").strip()
        except AttributeError:
            auth_cfg = None
        return cls(
            id=uuid.UUID(identifier),
            name=settings.value("name"),
            url=settings.value("url"),
            page_size=int(settings.value("page_size", defaultValue=10)),
            auth_config=auth_cfg,
        )


class SettingsManager(QtCore.QObject):
    """Manages saving/loading settings for the plugin in QgsSettings.
    """

    BASE_GROUP_NAME: str = "qgis_stac"
    CONNECTION_GROUP_NAME: str = "connections"
    SELECTED_CONNECTION_KEY: str = "selected_connection"

    settings = QgsSettings()

    connections_settings_updated = QtCore.pyqtSignal(str)

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
        self.connections_settings_updated.emit("")

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
        with qgis_settings(settings_key) as settings:
            settings.setValue("name", connection_settings.name)
            settings.setValue("url", connection_settings.url)
            settings.setValue("page_size", connection_settings.page_size)
            settings.setValue("auth_config", connection_settings.auth_config)
        self.connections_settings_updated.emit("")

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
        self.connections_settings_updated.emit("")

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
        self.connections_settings_updated.emit("")

    def clear_current_connection(self):
        """Removes the current selected connection in the settings.
        """
        with qgis_settings(self.BASE_GROUP_NAME) as settings:
            settings.setValue(self.SELECTED_CONNECTION_KEY, None)
        self.connections_settings_updated.emit("")

    def is_current_connection(self, identifier: uuid.UUID):
        """Checks if the connection with the passed identifier
            is the current selected connection.

        :param identifier: Connection settings identifier.
        :type identifier: uuid.UUID
        """
        current = self.get_current_connection()
        return False if current is None else current.id == identifier

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

    def store_search_filters(self, filters):
        raise NotImplementedError

    def get_search_filters(self):
        raise NotImplementedError


settings_manager = SettingsManager()
