# -*- coding: utf-8 -*-
"""
    Assets dialog, shows all the available assets.
"""

import os

from pathlib import Path
from osgeo import ogr

from functools import partial

from qgis import processing

from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.PyQt.uic import loadUiType

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsMapLayer,
    QgsNetworkContentFetcherTask,
    QgsPointCloudLayer,
    QgsProject,
    QgsProcessing,
    QgsProcessingFeedback,
    QgsRasterLayer,
    QgsTask,
    QgsVectorLayer,

)

from ..resources import *

from ..api.models import (
    AssetLayerType,
)

from ..conf import (
    Settings,
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
        self.vis_url_string = '/vsicurl/'
        self.download_result = {}
        self.load_assets = {}
        self.download_assets = {}

        self.load_btn.clicked.connect(self.load_btn_clicked)
        self.download_btn.clicked.connect(self.download_btn_clicked)

        self.prepare_assets()

        self.layers = {}

    def prepare_assets(self):
        """ Loads the dialog with the list of assets.
        """

        if len(self.assets) > 0:
            self.title.setText(
                tr("Item {}").
                format(self.item.id, len(self.assets))
            )
            self.asset_count.setText(
                tr("{} available asset(s)").
                format(len(self.assets))

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

            load_selected_partial = partial(
                self.load_asset_selected,
                asset,
            )

            download_selected_partial = partial(
                self.download_asset_selected,
                asset,
            )

            load_deselected_partial = partial(
                self.load_asset_deselected,
                asset,
            )

            download_deselected_partial = partial(
                self.download_asset_deselected,
                asset,
            )

            asset_widget.load_selected.connect(load_selected_partial)
            asset_widget.download_selected.connect(download_selected_partial)

            asset_widget.load_deselected.connect(load_deselected_partial)
            asset_widget.download_deselected.connect(download_deselected_partial)

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

    def load_asset_selected(self, asset):
        self.load_assets[asset.title] = asset
        self.load_btn.setText(
            f"Add assets as layers ({len(self.load_assets.items())})"
        )

        self.load_btn.setEnabled(True)

    def download_asset_selected(self, asset):
        self.download_assets[asset.title] = asset
        self.download_btn.setText(
            f"Download the selected assets "
            f"({len(self.download_assets.items())})"
        )
        self.download_btn.setEnabled(True)

    def load_asset_deselected(self, asset):
        self.load_assets.pop(asset.title)
        self.load_btn.setText(
            f"Add selected assets as layers "
            f"({len(self.load_assets.items())})"
        ) if self.load_assets else \
            self.load_btn.setText(
                "Add selected assets as layers"
            )

        self.load_btn.setEnabled(len(self.load_assets.items()) > 0)

    def download_asset_deselected(self, asset):
        self.download_assets.pop(asset.title)
        self.download_btn.setText(
            f"Download the selected assets "
            f"({len(self.download_assets.items())})"
        ) if self.download_assets else \
            self.download_btn.setText(
                "Download the selected assets"
            )

        self.download_btn.setEnabled(
            len(self.download_assets.items()) > 0
        )

    def load_btn_clicked(self):
        for key, asset in self.load_assets.items():
            try:
                QgsTask.fromFunction(
                    'Load asset function',
                    self.load_asset(asset)
                )
            except Exception as err:
                log(tr("Error loading assets {}".format(err)))

    def download_btn_clicked(self):
        auto_asset_loading = settings_manager.get_value(
            Settings.AUTO_ASSET_LOADING,
            False,
            setting_type=bool
        )

        for key, asset in self.download_assets.items():
            try:
                QgsTask.fromFunction(
                    'Download asset function',
                    self.download_asset(asset, auto_asset_loading)
                )
            except Exception as err:
                log(tr("Error downloading asset {}, {}".format(asset.title, err)))

    def update_inputs(self, enabled):
        """ Updates the inputs widgets state in the main search item widget.

        :param enabled: Whether to enable the inputs or disable them.
        :type enabled: bool
        """
        self.scroll_area.setEnabled(enabled)
        self.parent.update_inputs(enabled)
        self.load_btn.setEnabled(
            enabled and len(self.load_assets.items()) > 0
        )
        self.download_btn.setEnabled(
            enabled and len(self.download_assets.items()) > 0
        )

    def download_asset(self, asset, load_asset=False):
        """ Downloads the passed asset into directory defined in the plugin settings.

        :param asset: Item asset
        :type asset: models.ResourceAsset

        :param load_asset: Whether to load an asset after download has finished.
        :type load_asset: bool
        """
        self.update_inputs(False)
        download_folder = settings_manager.get_value(
            Settings.DOWNLOAD_FOLDER
        )
        item_folder = os.path.join(download_folder, self.item.id) \
            if download_folder else None
        feedback = QgsProcessingFeedback()
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
        extension_suffix = extension.split('?')[0] if extension else ""
        title = f"{asset.title}{extension_suffix}"

        title = self.clean_filename(title)

        output = os.path.join(
            item_folder, title
        ) if item_folder else QgsProcessing.TEMPORARY_OUTPUT
        params = {'URL': url, 'OUTPUT': output}

        self.download_result["file"] = output

        layer_types = [
            AssetLayerType.COG.value,
            AssetLayerType.COPC.value,
            AssetLayerType.GEOTIFF.value,
            AssetLayerType.NETCDF.value,
        ]
        try:
            self.main_widget.show_message(
                tr("Download for file {} to {} has started."
                   ).format(
                    title,
                    item_folder
                ),
                level=Qgis.Info
            )
            self.main_widget.show_progress(
                f"Downloading {url}",
                minimum=0,
                maximum=100,
            )

            feedback.progressChanged.connect(
                self.main_widget.update_progress_bar
            )
            feedback.progressChanged.connect(self.download_progress)

            # After asset download has finished, load the asset
            # if it can be loaded as a QGIS map layer.
            if load_asset and asset.type in layer_types:
                asset.href = self.download_result["file"]
                asset.title = title
                asset.type = AssetLayerType.GEOTIFF.value \
                    if AssetLayerType.COG.value in asset.type else asset.type
                load_file = partial(self.load_file_asset, asset)
                feedback.progressChanged.connect(load_file)

            processing.run(
                "qgis:filedownloader",
                params,
                feedback=feedback
            )

        except Exception as e:
            self.main_widget.show_message(
                tr("Error in downloading file, {}").format(str(e))
            )

    def load_file_asset(self, asset, value):
        """Loads the passed asset into QGIS map canvas if the
        progress value indicates the download has finished.

        param asset: Item asset
        :type asset: models.ResourceAsset

        :param value: Download progress value
        :type value: int
        """
        if value == 100:
            self.load_asset(asset)

    def download_progress(self, value):
        """Tracks the download progress of value and updates
        the info message when the download has finished

        :param value: Download progress value
        :type value: int
        """
        if value == 100:
            self.update_inputs(True)
            self.main_widget.show_message(
                tr("Download for file {} has finished."
                   ).format(
                    self.download_result["file"]
                ),
                level=Qgis.Info
            )

    def clean_filename(self, filename):
        """ Creates a safe filename by removing operating system
        invalid filename characters.

        :param filename: File name
        :type filename: str
        """
        characters = " %:/,\[]<>*?"

        for character in characters:
            if character in filename:
                filename = filename.replace(character, '_')

        return filename

    def load_asset(self, asset):
        """ Loads asset into QGIS.
            Checks if the asset type is a loadable layer inside QGIS.

        :param asset: Item asset
        :type asset: models.ResourceAsset
        """

        assert_type = asset.type
        raster_types = ','.join([
            AssetLayerType.COG.value,
            AssetLayerType.GEOTIFF.value,
            AssetLayerType.NETCDF.value
        ])
        vector_types = ','.join([
            AssetLayerType.GEOJSON.value,
            AssetLayerType.GEOPACKAGE.value
        ])
        point_cloud_types = ','.join([
            AssetLayerType.COPC.value,
        ])

        if assert_type in raster_types:
            layer_type = QgsMapLayer.RasterLayer
        elif assert_type in vector_types:
            layer_type = QgsMapLayer.VectorLayer
        elif assert_type in point_cloud_types:
            layer_type = QgsMapLayer.PointCloudLayer

        if assert_type in ''.join([AssetLayerType.COG.value]) or \
                assert_type in ''.join([AssetLayerType.NETCDF.value]):
            asset_href = f"{self.vis_url_string}" \
                         f"{asset.href}"
        else:
            asset_href = f"{asset.href}"
        asset_name = asset.title

        self.update_inputs(False)
        layer_loader = LayerLoader(
            asset_href,
            asset_name,
            layer_type
        )

        add_layer_partial = partial(
            self.add_layer,
            asset_name,
            layer_loader
        )

        # Using signal approach to detect the results of the layer loader
        # task as the callback function approach doesn't make the task
        # to recall the assigned callbacks in the provided context.
        layer_loader.taskCompleted.connect(add_layer_partial)
        layer_loader.progressChanged.connect(self.main_widget.update_progress_bar)
        layer_loader.taskTerminated.connect(self.layer_loader_terminated)

        QgsApplication.taskManager().addTask(layer_loader)

        self.main_widget.show_progress(
            f"Adding asset \"{asset_name}\" into QGIS",
            minimum=0,
            maximum=100,
        )
        self.main_widget.update_progress_bar(0)
        log(tr("Started adding asset into QGIS"))

    def add_layer(self, asset_name, layer_loader):
        """ Adds layer into the current QGIS project.
            For the layer to be added successfully, the task for loading
            layer need to exist and the corresponding layer need to be
            available.
        """
        if layer_loader and layer_loader.layer:
            layer = layer_loader.layer
            QgsProject.instance().addMapLayer(layer)

            message = tr(
                "Sucessfully added asset {} as a map layer "
            ).format(
                asset_name
            )
            level = Qgis.Info
        elif layer_loader and layer_loader.layers:
            layers = layer_loader.layers
            for layer in layers:
                QgsProject.instance().addMapLayer(layer)

            message = tr("Sucessfully added asset as a map layer(s)")
            level = Qgis.Info
        elif layer_loader and layer_loader.error:
            message = layer_loader.error
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
        elif self.layer_type is QgsMapLayer.PointCloudLayer:
            self.layer = QgsPointCloudLayer(
                self.layer_uri,
                self.layer_name,
                'copc'
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
            )if self.layer and self.layer.dataProvider() else None
            self.error = tr(
                f"Couldn't load layer "
                f"{self.layer_uri},"
                f"{provider_error}"
            )
            log(
                self.error
            )
