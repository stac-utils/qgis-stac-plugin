import os

from qgis.PyQt import QtCore, QtGui, QtNetwork, QtWidgets, QtXml
from qgis.PyQt.uic import loadUiType

from ..resources import *
from ..gui.connection_dialog import ConnectionDialog

from ..conf import settings_manager
from ..api.models import ItemSearch
from ..api.client import Client

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

        self.search_btn.clicked.connect(
            self.search_api
        )

        self.api_client = None
        self.connections_cmb.activated.connect(self.update_current_connection)
        self.update_current_connection(self.connections_cmb.currentIndex())

    def add_connection(self):
        connection_dialog = ConnectionDialog()
        connection_dialog.exec_()

    def update_current_connection(self, index):
        connection_name = self.connections_cmb.currentText()
        connection_settings = settings_manager. \
            find_connection_by_name(connection_name)
        self.api_client = Client.from_connection_settings(
            connection_settings
        )
        self.api_client.items_received.connect(self.display_results)
        self.api_client.error_received.connect(self.display_search_error)

    def search_api(self):
        start_dte = self.start_dte.dateTime()
        end_dte = self.end_dte.dateTime()
        self.api_client.get_items(
            ItemSearch(
                start_datetime=(
                    start_dte if not start_dte.isNull() else None
                ),
                end_datetime=(
                    end_dte if not end_dte.isNull() else None
                )
            )
        )

    def display_results(self):
        raise NotImplementedError

    def display_search_error(self):
        raise NotImplementedError
