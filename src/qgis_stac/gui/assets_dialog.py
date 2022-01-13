# -*- coding: utf-8 -*-
"""
    Assets dialog, shows all the available assets.
"""

import os

from pathlib import Path
from osgeo import ogr

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

from ..api.models import (
    AssetLayerType,
    Settings,
)

from qgis.PyQt import QtCore, QtGui, QtWidgets

from qgis.core import Qgis

from qgis.PyQt.uic import loadUiType

from ..conf import (
    settings_manager
)

from .asset_widget import AssetWidget

from ..utils import log, tr

DialogUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/item_assets_widget.ui")
)


class AssetsDialog(QtWidgets.QDialog, DialogUi):
    """ Dialog for adding and downloading STAC Item assets"""

    def __init__(
            self,
            item,
            parent,
            main_widget
    ):
        """ Constructor

        :param item: Item object with assets that are to be shown.
        :type item: model.Item

        :param parent Parent widget
        :type parent: QWidget

        :param main_widget: Plugin main widget
        :type main_widget: QWidget
        """
        super().__init__()
        self.setupUi(self)
        self.item = item
        self.assets = item.assets
        self.parent = parent
        self.main_widget = main_widget
        self.cog_string = '/vsicurl/'

        self.prepare_assets()

    def prepare_assets(self):
        """ Loads the dialog with the list of assets.
        """

        if len(self.assets) > 0:
            self.title.setText(
                tr("Item {}, has {} asset(s) available").
                format(self.item.id, len(self.assets))
            )
        else:
            self.title.setText(
                tr("Item {} has no assets").
                format(len(self.item.id))
            )

        scroll_container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(1)
        for asset in self.assets:
            asset_widget = AssetWidget(asset, self)

            layout.addWidget(asset_widget)
            layout.setAlignment(asset_widget, QtCore.Qt.AlignTop)
        vertical_spacer = QtWidgets.QSpacerItem(
            20,
            40,
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding
        )
        layout.addItem(vertical_spacer)
        scroll_container.setLayout(layout)
        self.scroll_area.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff
        )
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(scroll_container)

    def update_inputs(self, enabled):
        """ Updates the inputs widgets state in the main search item widget.

        :param enabled: Whether to enable the inputs or disable them.
        :type enabled: bool
        """
        self.scroll_area.setEnabled(enabled)
        self.parent.update_inputs(enabled)

    def download_asset(self, asset):
        """ Download asset into directory defined in the plugin settings.

        :param asset: Item asset
        :type asset: models.ResourceAsset
        """
        download_folder = settings_manager.get_value(
            Settings.DOWNLOAD_FOLDER
        )
        item_folder = os.path.join(download_folder, self.item.id) \
            if download_folder else None
        try:
            if item_folder:
                os.mkdir(item_folder)
        except FileExistsError as fe:
            pass
        except FileNotFoundError as fn:
            self.main_widget.show_message(
                tr("Folder {} is not found").format(download_folder),
                Qgis.Critical
            )
            return
        except PermissionError as pe:
            self.main_widget.show_message(
                tr("Permission error writing in download folder"),
                Qgis.Critical
            )
            return

        url = asset.href
        extension = Path(url).suffix
        title = f"{asset.title}{extension}"

        output = os.path.join(
            item_folder, title
        ) if item_folder else None
        params = {'URL': url, 'OUTPUT': output} \
            if item_folder else \
            {'URL': url}
        try:
            self.main_widget.show_message(
                tr("Download for file {} to {} has started."
                   "View Processing log for the download progress"
                   ).format(
                    title,
                    item_folder
                ),
                level=Qgis.Info
            )
            processing.run("qgis:filedownloader", params)
        except Exception as e:
            self.main_widget.show_message(
                tr("Error in downloading file, {}").format(str(e))
            )

    def load_asset(self, asset):
        """ Loads asset into QGIS.
            Checks if the asset type is a loadable layer inside QGIS.

        :param asset: Item asset
        :type asset: models.ResourceAsset
        """

        assert_type = asset.type
        types = {
            QgsMapLayer.RasterLayer: [AssetLayerType.COG, AssetLayerType.GEOTIFF],
            QgsMapLayer.VectorLayer: [AssetLayerType.GEOJSON, AssetLayerType.GEOPACKAGE]
        }
        if assert_type in AssetLayerType.COG.value or \
            assert_type in AssetLayerType.GEOTIFF.value:
            layer_type = QgsMapLayer.RasterLayer
        elif assert_type in AssetLayerType.GEOJSON.value or \
            assert_type in AssetLayerType.GEOPACKAGE.value:
            layer_type = QgsMapLayer.VectorLayer

        if AssetLayerType.COG.value in assert_type:
            asset_href = f"{self.cog_string}" \
                         f"{asset.href}"
        else:
            asset_href = f"{asset.href}"
        asset_name = asset.title

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
        elif self.layer_loader and self.layer_loader.layers:
            layers = self.layer_loader.layers
            for layer in layers:
                QgsProject.instance().addMapLayer(layer)

            message = tr("Sucessfully added asset as a map layer(s)")
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
        self.layers = []

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
            extension = Path(self.layer_uri).suffix
            result = False

            if extension is not ".gpkg":
                self.layer = QgsVectorLayer(
                    self.layer_uri,
                    self.layer_name,
                    AssetLayerType.VECTOR.value
                )
                result = self.layer.isValid()
            else:
                gpkg_connection = ogr.Open(self.layer_uri)

                for layer_item in gpkg_connection:
                    layer = QgsVectorLayer(
                        f"{gpkg_connection}|layername={layer_item.GetName()}",
                        layer_item.GetName(),
                        AssetLayerType.VECTOR.value
                    )
                    self.layers.append(layer.clone())
                    # If any layer from the geopackage is valid, load it.
                    if layer.isValid():
                        self.layer = layer
                        result = True
            return result
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
                f"Fetched layer with URI "
                f"{self.layer_uri} "
            )
            # Due to the way QGIS is handling layers sharing between tasks and
            # the main thread, sending the layer to the main thread
            # without cloning it can lead to unpredicted crashes,
            # hence we clone the layer before storing it, so it can
            # be used in the main thread.
            self.layer = self.layer.clone()
        else:
            provider_error = tr("error {}").format(
                self.layer.dataProvider().error()
            )if self.layer else ""
            self.error = tr(
                f"Couldn't load layer "
                f"{self.layer_uri},"
                f"{provider_error}"
            )
            log(
                self.error
            )
