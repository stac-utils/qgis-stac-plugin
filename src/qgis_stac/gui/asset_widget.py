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

from ..utils import log, tr

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
            "image/tiff; "
            "application=geotiff; "
            "profile=cloud-optimized"
        ]

        self.title_la.setText(self.asset.title)
        load_asset = partial(
            self.asset_dialog.load_asset,
            self.asset
        )
        download_asset = partial(
            self.asset_dialog.download_asset,
            self.asset
        )
        self.load_btn.setEnabled(self.asset.type in layer_types)
        self.load_btn.clicked.connect(load_asset)
        self.download_btn.clicked.connect(download_asset)

        if self.asset.type not in layer_types:
            self.load_btn.setTooltip(
                tr("Asset cannot be loaded as layer in QGIS")
            )
