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

from ..utils import tr

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/asset_widget.ui")
)


class AssetWidget(QtWidgets.QWidget, WidgetUi):
    """ Widget that provide UI for asset details,
    assets loading and downloading functionalities
    """

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
            AssetLayerType.GEOTIFF.value,
            AssetLayerType.NETCDF.value,
        ]

        self.title_la.setText(self.asset.title)
        load_asset = partial(
            self.asset_dialog.load_asset,
            self.asset
        )
        download_asset = partial(
            self.asset_dialog.download_asset,
            self.asset,
            True
        )
        self.load_btn.setEnabled(self.asset.type in layer_types)
        self.load_btn.clicked.connect(load_asset)
        self.download_btn.clicked.connect(download_asset)

        if self.asset.type not in layer_types:
            self.load_btn.setToolTip(
                tr("Asset contains a {} media type which"
                   "cannot be loaded as a map layer in QGIS"
                   ).format(self.asset.type)
            )
