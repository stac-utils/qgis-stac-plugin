# -*- coding: utf-8 -*-
"""
    Result item widget, used as a template for each search result item.
"""

import os

import json
import tempfile
import datetime

from functools import partial

from qgis.PyQt import (
    QtGui,
    QtCore,
    QtWidgets,
    QtNetwork
)
from qgis.PyQt.uic import loadUiType

from qgis import processing

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsMapLayer,
    QgsNetworkContentFetcherTask,
    QgsProject,
    QgsRasterLayer,
    QgsTask,
    QgsVectorLayer,

)

from ..resources import *
from ..utils import log, tr

from ..api.models import (
    AssetLayerType,
    AssetRoles,
    Settings,
)

from ..conf import settings_manager


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
        self.date_format = "%Y-%m-%dT%H:%M:%S"
        self.main_widget = main_widget
        self.layer_loader = None
        self.initialize_ui()
        if self.thumbnail_url:
            self.add_thumbnail()

    def initialize_ui(self):
        """ Populate UI inputs when loading the widget"""

        datetime_str = datetime.datetime.strftime(
            self.item.properties.resource_datetime,
            self.date_format
        ) if self.item.properties else ""

        self.created_date.setText(
            datetime_str
        )

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
        self.assets_download_box.activated.connect(self.download_asset)
        # make sure the palette highlight colors are the same
        self.assets_load_box.setStyleSheet(
            'selection-background-color: rgb(32, 100, 189);'
            'selection-color: white;'
        )
        self.assets_download_box.setStyleSheet(
            'selection-background-color: rgb(32, 100, 189);'
            'selection-color: white;'
        )

        self.footprint_box.setEnabled(self.item.stac_object is not None)
        self.footprint_box.clicked.connect(self.add_footprint)

    def add_footprint(self):
        """ Adds the item footprint inside QGIS as a map layer"""
        layer_file = tempfile.NamedTemporaryFile(
            mode="w+",
            suffix='.geojson',
            delete=False
        )
        layer_name = f"{self.item.id}_footprint"
        json.dump(self.item.stac_object.to_dict(), layer_file)

        layer_file.flush()

        layer = QgsVectorLayer(
            layer_file.name,
            layer_name,
            AssetLayerType.VECTOR.value
        )
        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            self.main_widget.show_message(
                tr("Successfully loaded footprint layer."),
                level=Qgis.Info
            )

        else:
            self.main_widget.show_message(
                tr(
                    "Couldn't load footprint into QGIS,"
                    " its layer is not valid."
                ),
                level=Qgis.Critical
            )

    def update_inputs(self, enabled):
        """ Updates the inputs widgets state in the main search item widget.

        :param enabled: Whether to enable the inputs or disable them.
        :type enabled: bool
        """
        self.assets_load_box.setEnabled(enabled)
        self.assets_download_box.setEnabled(enabled)
        self.footprint_box.setEnabled(enabled)

    def download_asset(self, index):
        """ Download asset into directory defined in the plugin settings.

        :param index: Index of the selected combo box item
        :type index: int
        """
        if self.assets_download_box.count() < 1 or index < 1:
            return
        download_folder = settings_manager.get_value(
            Settings.DOWNLOAD_FOLDER
        )
        url = self.assets_download_box.itemData(index)
        output = os.path.join(
            download_folder, self.assets_download_box.currentText()
        ) if download_folder else None
        params = {'URL': url, 'OUTPUT': output} \
            if download_folder else \
            {'URL': url}
        try:
            self.main_widget.show_message(
                tr("Download for file {} to {} has started."
                   "View Processing log for the download progress"
                   ).format(
                    self.assets_download_box.currentText(),
                    download_folder
                ),
                level=Qgis.Info
            )
            processing.run("qgis:filedownloader", params)
        except Exception as e:
            self.main_widget.show_message("Error in downloading file")

    def load_asset(self, index):
        """ Loads asset into QGIS.
            Checks if the asset type is a loadable layer inside QGIS.

        :param index: Index of the selected combo box item
        :type index: int
        """

        if self.assets_load_box.count() < 1 or index < 1:
            return
        assert_type = self.assets_load_box.itemData(index)['type']
        layer_type = QgsMapLayer.RasterLayer

        if AssetLayerType.COG.value in assert_type:
            asset_href = f"{self.cog_string}" \
                         f"{self.assets_load_box.itemData(index)['href']}"
        else:
            asset_href = f"{self.assets_load_box.itemData(index)['href']}"
        asset_name = self.assets_load_box.itemText(index)

        self.update_inputs(False)
        self.layer_loader = LayerLoader(
            asset_href,
            asset_name,
            layer_type
        )

        # Using signal approach to detect the results of the layer loader
        # task as the callback function approach doesn't make the task
        # to recall the assigned callbacks in the provided context.
        self.layer_loader.taskCompleted.connect(self.add_layer)
        self.layer_loader.progressChanged.connect(self.main_widget.update_progress_bar)
        self.layer_loader.taskTerminated.connect(self.layer_loader_terminated)

        QgsApplication.taskManager().addTask(self.layer_loader)

        self.main_widget.show_progress(
            f"Adding asset \"{asset_name}\" into QGIS",
            minimum=0,
            maximum=100,
        )
        self.main_widget.update_progress_bar(0)
        log(tr("Started adding asset into QGIS"))

    def add_layer(self):
        """ Adds layer into the current QGIS project.
            For the layer to be added successfully, the task for loading
            layer need to exist and the corresponding layer need to be
            available.
        """
        if self.layer_loader and self.layer_loader.layer:
            layer = self.layer_loader.layer
            QgsProject.instance().addMapLayer(layer)

            message = tr("Sucessfully added asset as a map layer")
            level = Qgis.Info
        elif self.layer_loader and self.layer_loader.error:
            message = self.layer_loader.error
            level = Qgis.Critical
        else:
            message = tr("Problem fetching asset and loading it, into QGIS")
            level = Qgis.Critical

        self.update_inputs(True)
        log(message)
        self.main_widget.show_message(
            message,
            level=level
        )

    def layer_loader_terminated(self):
        """ Shows message to user when layer loading task has been terminated"""
        message = tr("QGIS background task for loading assets was terminated.")
        self.update_inputs(True)
        log(message)
        self.main_widget.show_message(
            message,
            level=Qgis.Critical
        )

    def handle_layer_error(self, message):
        """ Handles the error message from the layer loading task

        :param message: The error message
        :type message: str
        """
        self.update_inputs(True)
        log(message)
        self.main_widget.show_message(
            message
        )

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
            log(tr("Problem fetching response from network"))


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
            log(tr("Couldn't load thumbnail"))


class LayerLoader(QgsTask):
    """ Prepares and loads items as assets inside QGIS as layers."""
    def __init__(
        self,
        layer_uri,
        layer_name,
        layer_type
    ):

        super().__init__()
        self.layer_uri = layer_uri
        self.layer_name = layer_name
        self.layer_type = layer_type
        self.error = None
        self.layer = None

    def run(self):
        """ Operates the main layers loading logic
        """
        log(
            tr("Fetching layers in a background task.")
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
                AssetLayerType.VECTOR.value
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
                f"Fetched layer with URI"
                f"{self.layer_uri} "
            )
            # Due to the way QGIS is handling layers sharing between tasks and
            # the main thread, sending the layer to the main thread
            # without cloning it can lead to unpredicted crashes,
            # hence we clone the layer before storing it, so it can
            # be used in the main thread.
            self.layer = self.layer.clone()
        else:
            self.error = tr(
                f"Couldn't load layer "
                f"{self.layer_uri},"
                f"error {self.layer.dataProvider().error()}"
            )
            log(
                self.error
            )
