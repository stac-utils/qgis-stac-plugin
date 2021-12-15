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
    QgsMapLayer,
    QgsNetworkContentFetcherTask,
    QgsProject,
    QgsRasterLayer,
    QgsTask,
    QgsVectorLayer,

)

from ..resources import *
from ..utils import log

from ..api.models import AssetLayerType, AssetRoles


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
        main_widget,
        parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.item = item
        self.title_la.setText(item.id)
        self.collection_name.setText(item.collection)
        self.thumbnail_url = None
        self.cog_string = '/vsicurl/'
        self.main_widget = main_widget
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
                    {
                        "href": asset.href,
                        "type": asset.type,
                    }
                )
            if AssetRoles.THUMBNAIL.value in asset.roles:
                self.thumbnail_url = asset.href

        self.assets_load_box.activated.connect(self.load_asset)
        # self.assets_load_box.currentIndexChanged(self.load_asset)

    def update_inputs(self, enabled):
        self.assets_load_box.setEnabled(enabled)
        self.assets_download_box.setEnabled(enabled)
        self.footprint_box.setEnabled(enabled)

    def load_asset(self, index):
        """ Loads asset into QGIS"""

        if self.assets_load_box.count() < 1 or index < 1:
            return
        assert_type = self.assets_load_box.itemData(index)['type']

        if AssetLayerType.COG.value in assert_type:
            asset_href = f"{self.cog_string}" \
                         f"{self.assets_load_box.itemData(index)['href']}"
        else:
            asset_href = f"{self.assets_load_box.itemData(index)['href']}"
        asset_name = self.assets_load_box.itemText(index)

        self.update_inputs(False)
        layer_loader = LayerLoader(
            asset_href,
            asset_name,
            QgsMapLayer.RasterLayer,
            self.add_layer,
            self.handle_layer_error
        )

        self.main_widget.show_progress(
            f"Adding asset {asset_name} into QGIS"
        )

        log("Started adding asset into QGIS")
        QgsApplication.taskManager().addTask(layer_loader)

    def add_layer(self, layer):
        """ Adds layer into the current QGIS project

        :param layer: QGIS layer
        :type layer: QgsMapLayer
        """
        QgsProject.instance().addMapLayer(layer)
        self.update_inputs(True)
        self.main_widget.show_message(
            "Sucessfully added asset into QGIS"
        )
        log("Successfully added asset into QGIS")

    def handle_layer_error(self, message):
        """ Handles the error message from the layer loading task

        :param message: The error message
        :type message: str
        """
        self.update_inputs(True)
        self.main_widget.show_message(
            message
        )
        log(message)

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
            log("Couldn't load thumbnail")


class LayerLoader(QgsTask):
    """ Prepares and loads items as assets inside QGIS as layers."""
    def __init__(
        self,
        layer_uri,
        layer_name,
        layer_type,
        handler,
        error_handler
    ):

        super().__init__()
        self.layer_uri = layer_uri
        self.layer_name = layer_name
        self.layer_type = layer_type
        self.handler = handler
        self.error_handler = error_handler
        self.layer = None

    def run(self):
        """ Operates the main layers loading logic
        """
        log(
            "Fetching layers in a background task."
        )
        if self.layer_type is QgsMapLayer.RasterLayer:
            self.layer = QgsRasterLayer(
                self.layer_uri,
                self.layer_name
            )
            return self.layer.isValid()
        elif self.layer_type is QgsMapLayer.VectorLayer:
            self.layer = QgsVectorLayer(
                self.layer_uri,
                self.layer_name,
                "ogr"
            )
            return self.layer.isValid()
        else:
            raise NotImplementedError

        return False

    def finished(self, result: bool):
        """ Calls the handler responsible for adding the
         layer into QGIS project.

        :param result: Whether the run() operation finished successfully
        :type result: bool
        """
        if result and self.layer:
            log(
                f"Successfully fetched layer with URI"
                f"{self.layer_uri} "
            )
            # Due to the way QGIS is handling layers sharing between tasks and
            # the main thread, sending the layer to the main thread
            # without cloning it can lead to unpredicted crashes, hence we clone
            # the layer before sharing it with the main thread.
            layer = self.layer.clone()
            self.handler(layer)
        else:
            log(
                f"Couldn't load layer "
                f"{self.layer_uri}, "
                f"error {self.layer.dataProvider().error()}"
            )
            self.error_handler(
                f"Problem adding layer into QGIS,"
                f"{self.layer_uri},"
                f"error {self.layer.dataProvider().error()}"
            )
