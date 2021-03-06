# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QgisStac

 A QGIS plugin that provides support for accessing STAC APIs inside QGIS
 application.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2021-11-15
        copyright            : (C) 2021 by Kartoza
        email                : info@kartoza.com
        git sha              : $Format:%H$
 ***************************************************************************/
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""
import os
import sys

LIB_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'lib'))
if LIB_DIR not in sys.path:
    sys.path.append(LIB_DIR)


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load QgisStac class from file QgisStac.
    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .main import QgisStac

    return QgisStac(iface)
