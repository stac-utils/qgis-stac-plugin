# -*- coding: utf-8 -*-
"""
    Plugin utilities
"""

import datetime
import os
import subprocess
import sys
import uuid

from osgeo import gdal

from qgis.PyQt import QtCore, QtGui
from qgis.core import Qgis, QgsMessageLog

from .api.models import ApiCapability
from .conf import (
    ConnectionSettings,
    settings_manager
)

from .definitions.catalog import CATALOGS, SITE


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


def log(
        message: str,
        name: str = "qgis_stac",
        info: bool = True,
        notify: bool = True,
):
    """ Logs the message into QGIS logs using qgis_stac as the default
    log instance.
    If notify_user is True, user will be notified about the log.

    :param message: The log message
    :type message: str

    :param name: Name of te log instance, qgis_stac is the default
    :type message: str

    :param info: Whether the message is about info or a
    warning
    :type info: bool

    :param notify: Whether to notify user about the log
    :type notify: bool
     """
    level = Qgis.Info if info else Qgis.Warning
    QgsMessageLog.logMessage(
        message,
        name,
        level=level,
        notifyUser=notify,
    )


def config_defaults_catalogs():
    """ Initialize the plugin connections settings with the default
    catalogs and set the current connection active.
    """

    for catalog in CATALOGS:
        connection_id = uuid.UUID(catalog['id'])

        capability = ApiCapability(catalog["capability"]) \
            if catalog["capability"] else None
        if not settings_manager.is_connection(
                connection_id
        ):
            connection_settings = ConnectionSettings(
                id=connection_id,
                name=catalog['name'],
                url=catalog['url'],
                page_size=5,
                collections=[],
                conformances=[],
                capability=capability,
                created_date=datetime.datetime.now(),
                auth_config=None,
                sas_subscription_key=None,
                search_items=[],
            )
            settings_manager.save_connection_settings(connection_settings)

            if catalog['selected']:
                settings_manager.set_current_connection(connection_id)

    settings_manager.set_value("default_catalogs_set", True)


def open_folder(path):
    """ Opens the folder located at the passed path

    :param path: Folder path
    :type path: str

    :returns message: Message about whether the operation was
    successful or not.
    :rtype tuple
    """
    if not path:
        return False, tr("Path is not set")

    if not os.path.exists(path):
        return False, tr('Path do not exist: {}').format(path)

    if not os.access(path, mode=os.R_OK | os.W_OK):
        return False, tr('No read or write permission on path: {}').format(path)

    if sys.platform == 'darwin':
        subprocess.check_call(['open', path])
    elif sys.platform in ['linux', 'linux1', 'linux2']:
        subprocess.check_call(['xdg-open', path])
    elif sys.platform == 'win32':
        subprocess.check_call(['explorer', path])
    else:
        raise NotImplementedError

    return True, tr("Success")


def open_documentation():
    """ Opens documentation website in the default browser"""
    QtGui.QDesktopServices.openUrl(
        QtCore.QUrl(SITE)
    )


def check_gdal_version():
    """ Checks if the installed gdal version matches the
    required version by the plugin
    """
    gdal_version = gdal.VersionInfo("RELEASE_NAME")
    if int(gdal.VersionInfo("VERSION_NUM")) < 1000000:
        msg = tr(
            "Make sure you are using GDAL >= 1.10 "
            "You seem to have gdal {} installed".format(gdal_version))
        log(msg)

