import os
from functools import partial

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
    AssetRoles,
    Settings,
)

from qgis.PyQt import QtCore, QtGui, QtWidgets

from qgis.core import Qgis
from qgis.gui import QgsMessageBar

from qgis.PyQt.uic import loadUiType

from ..conf import (
    ConnectionSettings,
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
            assets,
            main_widget,
            connection=None
    ):
        """ Constructor

        :param assets: List of item assets
        :type assets: list

        :param connection: Connection settings
        :type connection: ConnectionSettings
        """
        super().__init__()
        self.setupUi(self)
        self.connection = connection
        self.assets = assets
        self.main_widget = main_widget
        self.cog_string = '/vsicurl/'

        # prepare model for the assets tree view
        self.model = QtGui.QStandardItemModel()
        self.proxy_model = QtCore.QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setDynamicSortFilter(True)
        self.proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.grid_layout = QtWidgets.QGridLayout()
        self.message_bar = QgsMessageBar()
        self.progress_bar = QtWidgets.QProgressBar()

        self.prepare_message_bar()
        self.prepare_assets()

    def prepare_assets(self):
        """ Loads the dialog list of assets into the assets
        scroll view
        """
        self.title.setText(tr("{} asset(s) available").format(len(self.assets)))
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
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(scroll_container)

    def update_inputs(self, enabled):
        """ Updates the inputs widgets state in the main search item widget.

        :param enabled: Whether to enable the inputs or disable them.
        :type enabled: bool
        """
        self.scroll_area.setEnabled(enabled)

    def download_asset(self, asset):
        """ Download asset into directory defined in the plugin settings.

        :param index: Index of the selected combo box item
        :type index: int
        """
        download_folder = settings_manager.get_value(
            Settings.DOWNLOAD_FOLDER
        )
        url = asset.href
        output = os.path.join(
            download_folder, asset.title
        ) if download_folder else None
        params = {'URL': url, 'OUTPUT': output} \
            if download_folder else \
            {'URL': url}
        try:
            self.main_widget.show_message(
                tr("Download for file {} to {} has started."
                   "View Processing log for the download progress"
                   ).format(
                    asset.title,
                    download_folder
                ),
                level=Qgis.Info
            )
            processing.run("qgis:filedownloader", params)
        except Exception as e:
            self.main_widget.show_message("Error in downloading file")

    def load_asset(self, asset):
        """ Loads asset into QGIS.
            Checks if the asset type is a loadable layer inside QGIS.

        :param index: Index of the selected combo box item
        :type index: int
        """

        assert_type = asset.type
        layer_type = QgsMapLayer.RasterLayer

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

    def prepare_message_bar(self):
        """ Initializes the widget message bar settings"""
        self.message_bar.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Fixed
        )
        self.grid_layout.addWidget(
            self.title,
            0, 0, 1, 1
        )
        self.grid_layout.addWidget(
            self.message_bar,
            0, 0, 1, 1,
            alignment=QtCore.Qt.AlignTop
        )
        self.layout().insertLayout(0, self.grid_layout)

    def show_message(
            self,
            message,
            level=Qgis.Warning
    ):
        """ Shows message on the main widget message bar

        :param message: Message text
        :type message: str

        :param level: Message level type
        :type level: Qgis.MessageLevel
        """
        self.message_bar.clearWidgets()
        self.message_bar.pushMessage(message, level=level)

    def show_progress(
            self,
            message,
            minimum=0,
            maximum=0,
            progress_bar=True):
        """ Shows the progress message on the main widget message bar

        :param message: Progress message
        :type message: str

        :param minimum: Minimum value that can be set on the progress bar
        :type minimum: int

        :param maximum: Maximum value that can be set on the progress bar
        :type maximum: int

        :param progress_bar: Whether to show progress bar status
        :type progress_bar: bool
        """
        self.message_bar.clearWidgets()
        message_bar_item = self.message_bar.createMessage(message)
        try:
            self.progress_bar.isEnabled()
        except RuntimeError as er:
            self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        if progress_bar:
            self.progress_bar.setMinimum(minimum)
            self.progress_bar.setMaximum(maximum)
        else:
            self.progress_bar.setMaximum(0)
        message_bar_item.layout().addWidget(self.progress_bar)
        self.message_bar.pushWidget(message_bar_item, Qgis.Info)


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
