# -*- coding: utf-8 -*-
"""
    Handles access to storage and retrieval of the plugin QgsSettings
"""

import contextlib
import dataclasses
import logging
import typing
import uuid

from qgis.PyQt import (
    QtCore,
    QtWidgets,
)
from qgis.core import QgsRectangle, QgsSettings
logger = logging.getLogger(__name__)


@contextlib.contextmanager
def qgis_settings(group_root: str):
    """
    Context manager to help defining groups when creating QgsSettings

    :param group_root: Name of the root group for the settings.
    :type group_root: str

    :yields: Instance of the created settings
    :type QgsSettings
    """
    settings = QgsSettings()
    settings.beginGroup(group_root)
    try:
        yield settings
    finally:
        settings.endGroup()


@dataclasses.dataclass
class ConnectionSettings:
    """Manages STAC API connection settings"""

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
        """ Reads QGIS settings and parses them into a connection
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
    """Manage saving/loading settings for the plugin in QgsSettings"""

    BASE_GROUP_NAME: str = "qgis_stac"
    CONNECTION_GROUP_NAME: str = "connections"
    SELECTED_CONNECTION_KEY: str = "selected_connection"

    current_connection_changed = QtCore.pyqtSignal(str)

    def list_connections(self) -> typing.List[ConnectionSettings]:
        """ Lists all the plugin connections stored in the QgsSettings.

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
        result.sort(key=lambda obj: obj.name)
        return result

    def delete_all_connections(self):
        """
        Deletes all the plugin connections settings in QgsSettings
        """
        with qgis_settings(
                f"{self.BASE_GROUP_NAME}"
                f"/{self.CONNECTION_GROUP_NAME}") \
                as settings:
            for connection_name in settings.childGroups():
                settings.remove(connection_name)
        self.clear_current_connection()

    def find_connection_by_name(self, name):
        """
        Finds a connection setting inside the plugin QgsSettings by name.

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
        """
         Gets the connection setting with the specified identifier.

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
            settings: ConnectionSettings):
        """
        Saves connection settings from the given connection settings object

        :param settings: Connection settings object
        :type settings: ConnectionSettings

        """
        settings_key = self._get_connection_settings_base(settings.id)
        with qgis_settings(settings_key) as settings:
            settings.setValue("name", settings.name)
            settings.setValue("url", settings.base_url)
            settings.setValue("page_size", settings.page_size)
            settings.setValue("auth_config", settings.auth_config)

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
            settings.remove(str(id))

    def get_current_connection(self) -> typing.Optional[ConnectionSettings]:
        """ Gets the current active connection from the QgsSettings

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
        self.current_connection_changed.emit(serialized_id)

    def clear_current_connection(self):
        """ Removes the selected connection settings.
        """
        with qgis_settings(self.BASE_GROUP_NAME) as settings:
            settings.setValue(self.SELECTED_CONNECTION_KEY, None)
        self.current_connection_changed.emit("")

    def is_current_connection(self, identifier: uuid.UUID):
        """ Checks if the connection with the passed identifier
            is the current selected connection.

        :param identifier: Connection settings identifier
        :type identifier: uuid.UUID
        """
        current = self.get_current_connection()
        return False if current is None else current.id == identifier

    def _get_connection_settings_base(
            self,
            identifier: typing.Union[str, uuid.UUID]):
        """ Gets the connection settings base url

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
