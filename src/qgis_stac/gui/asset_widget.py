# -*- coding: utf-8 -*-
"""
    Asset item widget, used as a template for each item asset.
"""

import os

from qgis.PyQt import (
    QtCore,
    QtGui,
    QtNetwork,
    QtWidgets,
)
from qgis.PyQt.uic import loadUiType

from qgis.core import QgsNetworkAccessManager

from ..api.models import AssetLayerType

from ..utils import log, tr

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

        self.title_la.setText(self.asset.title)
        self.type_la.setText(self.asset.type)
        asset_load = self.asset_loadable()

        self.load_box.setEnabled(asset_load)
        self.load_box.toggled.connect(self.asset_load_selected)
        self.load_box.stateChanged.connect(self.asset_load_selected)
        self.download_box.toggled.connect(self.asset_download_selected)
        self.download_box.stateChanged.connect(self.asset_download_selected)

        if asset_load:
            self.load_box.setToolTip(
                tr("Asset contains {} media type which "
                   "cannot be loaded as a map layer in QGIS"
                   ).format(self.asset.type)
            )

    def asset_loadable(self):
        """ Returns if asset can be added into QGIS"""

        layer_types = [
            AssetLayerType.COG.value,
            AssetLayerType.COPC.value,
            AssetLayerType.GEOTIFF.value,
            AssetLayerType.NETCDF.value,
        ]

        if self.asset.type is not None:
            return self.asset.type in ''.join(layer_types)
        else:
            try:
                request = QtNetwork.QNetworkRequest(
                    QtCore.QUrl(self.asset.href)
                )
                response = QgsNetworkAccessManager().\
                    instance().blockingGet(request)
                content_type = response.rawHeader(
                    QtCore.QByteArray(
                        'content-type'.encode()
                    )
                )
                content_type = str(content_type, 'utf-8')

                for layer_type in layer_types:
                    layer_type_values = layer_type.split(' ')
                    for value in layer_type_values:
                        if value in content_type:
                            return True

            except Exception as e:
                log(f"Problem fetching asset "
                    f"type from the asset url {self.asset.href},"
                    f" error {e}"
                    )

            return False

    def asset_load_selected(self, state=None):
        """ Emits the needed signal when an asset has been selected
        for loading.
        """
        if self.load_box.isChecked():
            self.load_selected.emit()
        else:
            self.load_deselected.emit()

    def asset_download_selected(self, state=None):
        """ Emits the needed signal when an asset has been selected
            for downloading.
            """
        if self.download_box.isChecked():
            self.download_selected.emit()
        else:
            self.download_deselected.emit()
