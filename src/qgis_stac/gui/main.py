import os

from qgis.PyQt import QtCore, QtGui, QtNetwork, QtWidgets, QtXml
from qgis.PyQt.uic import loadUiType

from ..resources import *

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/qgis_stac_widget.ui")
)


class QgisStacWidget(QtWidgets.QWidget, WidgetUi):

    def __init__(
            self,
            parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
