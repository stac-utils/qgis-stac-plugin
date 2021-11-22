import os
from qgis.PyQt import QtWidgets
from qgis.PyQt.uic import loadUiType


DialogUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/connection_dialog.ui")
)


class ConnectionDialog(QtWidgets.QDialog, DialogUi):
    def __init__(
            self,
            parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)