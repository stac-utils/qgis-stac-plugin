# -*- coding: utf-8 -*-
"""
    Plugin utilities
"""
import uuid
import datetime

from qgis.PyQt import QtCore
from .conf import (
    ConnectionSettings,
    settings_manager
)

from .definitions.catalog import CATALOGS


def tr(message):
    """Get the translation for a string using Qt translation API.
    We implement this ourselves since we do not inherit QObject.

    :param message: String for translation.
    :type message: str, QString

    :returns: Translated version of message.
    :rtype: QString
    """
    # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
    return QtCore.QCoreApplication.translate("QgisStac", message)


def config_defaults_catalogs():
    """ Initialize the plugin connections settings with the default
    catalogs and set the current connection active.
    """

    for catalog in CATALOGS:
        connection_id = uuid.UUID(catalog['id'])
        if not settings_manager.is_connection(
                connection_id
        ):
            connection_settings = ConnectionSettings(
                id=connection_id,
                name=catalog['name'],
                url=catalog['url'],
                page_size=5,
                created_date=datetime.datetime.now(),
                auth_config=None,
            )
            settings_manager.save_connection_settings(connection_settings)

            if catalog['selected']:
                settings_manager.set_current_connection(connection_id)

    settings_manager.set_value("default_catalogs_set", True)
