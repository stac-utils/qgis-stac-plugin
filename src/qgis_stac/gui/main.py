import os

from qgis.PyQt import QtCore, QtGui, QtNetwork, QtWidgets, QtXml
from qgis.PyQt.uic import loadUiType

from ..conf import settings_manager
from ..resources import *
from ..gui.connection_dialog import ConnectionDialog

from ..conf import settings_manager
from ..api.models import ItemSearch
from ..api.client import Client

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/qgis_stac_widget.ui")
)


class QgisStacWidget(QtWidgets.QWidget, WidgetUi):
    """ Main plugin widget that has tabs for search, results and settings."""
    def __init__(
            self,
            parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.new_connection_btn.clicked.connect(self.add_connection)
        self.connections_box.currentIndexChanged.connect(
            self.update_connection_buttons
        )
        self.update_connections_combobox()
        self.update_connection_buttons()
        self.connections_box.activated.connect(self.update_current_connection)
        self.pagination.setVisible(False)

        self.search_btn.clicked.connect(
            self.search_api
        )

        self.api_client = None
        self.connections_cmb.activated.connect(self.update_current_connection)
        self.update_current_connection(self.connections_cmb.currentIndex())

    def add_connection(self):
        """ Adds a new connection into the plugin, then updates
        the connections combo box list to show the added connection.
        """
        connection_dialog = ConnectionDialog()
        connection_dialog.exec_()
        self.update_connections_combobox()

    def update_connection_buttons(self):
        """ Updates the edit and delete connection buttons state
        """
        current_name = self.connections_cmb.currentText()
        enabled = current_name != ""
        self.edit_connection_btn.setEnabled(enabled)
        self.delete_connection_btn.setEnabled(enabled)

    def update_current_connection(self, current_index: int):
        current_text = self.connections_cmb.itemText(current_index)
        if current_text == "":
            return
        current_connection = settings_manager.\
            find_connection_by_name(current_text)
        settings_manager.set_current_connection(current_connection.id)
        self.api_client = Client.from_connection_settings(
            current_connection
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

    def update_connections_combobox(self):
        """ Updates connections list displayed on the connection
        combox box to contain latest list of the connections.
        """
        existing_connections = settings_manager.list_connections()
        self.connections_cmb.clear()
        if len(existing_connections) > 0:
            self.connections_cmb.addItems(conn.name for conn in existing_connections)
            current_connection = settings_manager.get_current_connection()
            if current_connection is not None:
                current_index = self.connections_cmb.findText(current_connection.name)
                self.connections_cmb.setCurrentIndex(current_index)
            else:
                self.connections_cmb.setCurrentIndex(0)

    def update_current_connection(self, current_index: int):
        """ Sets the select connection from the connection combo box as the
        current selected connection.

        :param current_index: Index of the selected item from the connection combo
        box
        :type current_index: int
        """
        current_text = self.connections_cmb.itemText(current_index)
        if current_text != "":
            current_connection = settings_manager.\
                find_connection_by_name(current_text)
            settings_manager.set_current_connection(
                current_connection.id
            )

