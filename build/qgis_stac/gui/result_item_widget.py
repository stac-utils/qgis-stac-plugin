# -*- coding: utf-8 -*-
"""
    Result item widget, used as a template for each search result item.
"""

import os

from functools import partial

from qgis.PyQt import (
    QtGui,
    QtCore,
    QtWidgets,
    QtNetwork
)

from qgis.PyQt.uic import loadUiType

from  qgis.core import (
    QgsApplication,
    QgsNetworkContentFetcherTask,
    QgsTask
)

from ..resources import *
from ..utils import log

from ..api.models import AssetRoles


WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/result_item_widget.ui")
)


class ResultItemWidget(QtWidgets.QWidget, WidgetUi):
    """
     Result item widget class, contains logic for displaying the
     item properties, loading and downloading item assets as layers,
     showing the item thumbnail and adding footprint as
     a layer into QGIS.
    """

    def __init__(
        self,
        item,
        parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.item = item
        self.title_la.setText(item.id)
        self.collection_name.setText(item.collection)
        self.thumbnail_url = None
        self.initialize_ui()
        # if self.thumbnail_url:
        #     self.add_thumbnail()

    def initialize_ui(self):
        """ Populate UI inputs when loading the widget"""

        self.created_date.setText(
            str(self.item.properties.resource_datetime)
        ) if self.item.properties else None

        layer_types = [
            "image/tiff; "
            "application=geotiff; "
            "profile=cloud-optimized"
        ]

        for asset in self.item.assets:
            self.assets_download_box.addItem(
                asset.title,
                asset.href
            )
            if asset.type in layer_types:
                self.assets_load_box.addItem(
                    asset.title,
                    asset.href
                )
            if AssetRoles.THUMBNAIL in asset.roles:
                self.thumbnail_url = asset.href

    def add_thumbnail(self):
        """ Downloads and loads the STAC Item thumbnail"""
        request = QtNetwork.QNetworkRequest(
            QtCore.QUrl(
                self.thumbnail_url
            )
        )
        self.network_task(
            request,
            self.thumbnail_response
        )

    def thumbnail_response(self, content):
        """ Callback to handle the thumbnail network response.
            Sets the thumbnail image data into the widget thumbnail label.

        :param content: Network response data
        :type content: QByteArray
        """
        thumbnail_image = QtGui.QImage.fromData(content)

        if thumbnail_image:
            thumbnail_pixmap = QtGui.QPixmap.fromImage(thumbnail_image)
            self.thumbnail_la.setPixmap(thumbnail_pixmap)

    def network_task(
            self,
            request,
            handler,
            auth_config=""
    ):
        """Fetches the response from the given request.

        :param request: Network request
        :type request: QNetworkRequest

        :param handler: Callback function to handle the response
        :type handler: Callable

        :param auth_config: Authentication configuration string
        :type auth_config: str
        """
        task = QgsNetworkContentFetcherTask(
            request,
            authcfg=auth_config
        )
        response_handler = partial(
            self.response,
            task,
            handler
        )
        task.fetched.connect(response_handler)
        task.run()

    def response(
            self,
            task,
            handler
    ):
        """Handle the return response

        :param task: QGIS task that fetches network content
        :type task:  QgsNetworkContentFetcherTask
        """
        reply = task.reply()
        error = reply.error()
        if error == QtNetwork.QNetworkReply.NoError:
            contents: QtCore.QByteArray = reply.readAll()
            handler(contents)
        else:
            log("Problem fetching response from network")


class ThumbnailLoader(QgsTask):
    """ Prepares and loads the passed thumbnail into the item widget."""
    def __init__(
        self,
        thumbnail_reply: QtCore.QByteArray,
        label: QtWidgets.QLabel
    ):

        super().__init__()
        self.content = thumbnail_reply
        self.label = label
        self.thumbnail_image = None

    def run(self):
        """ Operates the main logic of loading the thumbnail data in
        background.
        """
        self.thumbnail_image = QtGui.QImage.fromData(self.content)
        return True

    def finished(self, result: bool):
        """ Loads the thumbnail into the widget, if its image data has
        been successfully loaded.

        :param result: Whether the run() operation finished successfully
        :type result: bool
        """
        if result:
            thumbnail_pixmap = QtGui.QPixmap.fromImage(self.thumbnail_image)
            self.label.setPixmap(thumbnail_pixmap)
        else:
            log(f"Couldn't load thumbnail")
