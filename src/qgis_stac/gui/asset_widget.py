# -*- coding: utf-8 -*-
"""
    Asset item widget, used as a template for each item asset.
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

from ..api.models import AssetLayerType

from ..conf import Settings, settings_manager

from ..utils import tr

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/asset_widget.ui")
)


class AssetWidget(QtWidgets.QWidget, WidgetUi):
    """ Widget that provide UI for asset details,
    assets loading and downloading functionalities
    """

    load_selected = QtCore.pyqtSignal()
    download_selected = QtCore.pyqtSignal()

    load_deselected = QtCore.pyqtSignal()
    download_deselected = QtCore.pyqtSignal()

    def __init__(
        self,
        asset,
        asset_dialog,
        parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.asset = asset
        self.asset_dialog = asset_dialog

        self.initialize_ui()

    def initialize_ui(self):
        """ Populate UI inputs when loading the widget"""

        layer_types = [
            AssetLayerType.COG.value,
            AssetLayerType.COPC.value,
            AssetLayerType.GEOTIFF.value,
            AssetLayerType.NETCDF.value,
        ]

        self.title_la.setText(self.asset.title)
        self.type_la.setText(self.asset.type)

        self.load_box.setEnabled(self.asset.type in ''.join(layer_types))
        self.load_box.toggled.connect(self.asset_load_selected)
        self.download_box.toggled.connect(self.asset_download_selected)

        if self.asset.type not in layer_types:
            self.load_box.setToolTip(
                tr("Asset contains a {} media type which "
                   "cannot be loaded as a map layer in QGIS"
                   ).format(self.asset.type)
            )

    def asset_load_selected(self):
        if self.load_box.isChecked():
            self.load_selected.emit()
        else:
            self.load_deselected.emit()

    def asset_download_selected(self):
        if self.download_box.isChecked():
            self.download_selected.emit()
        else:
            self.download_deselected.emit()
