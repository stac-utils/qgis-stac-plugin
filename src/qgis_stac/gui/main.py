import os

from qgis.PyQt import QtCore, QtGui, QtNetwork, QtWidgets, QtXml
from qgis.PyQt.uic import loadUiType

from ..resources import *
from ..gui.connection_dialog import ConnectionDialog

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/qgis_stac_widget.ui")
)


class QgisStacWidget(QtWidgets.QWidget, WidgetUi):
    new_connection_btn: QtWidgets.QPushButton
    pagination: QtWidgets.QWidget

    def __init__(
            self,
            parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.new_connection_btn.clicked.connect(self.add_connection)
        self.pagination.setVisible(False)

    def add_connection(self):
        connection_dialog = ConnectionDialog()
        connection_dialog.exec_()
