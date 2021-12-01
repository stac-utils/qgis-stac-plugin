import os

from qgis.PyQt import QtCore, QtGui, QtNetwork, QtWidgets, QtXml
from qgis.PyQt.uic import loadUiType

from ..conf import settings_manager
from ..resources import *
from ..gui.connection_dialog import ConnectionDialog

from ..conf import settings_manager
from ..api.models import ItemSearch
from ..api.client import Client

from ..utils import tr

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/qgis_stac_widget.ui")
)


class QgisStacWidget(QtWidgets.QWidget, WidgetUi):
    """ Main plugin widget that contains tabs for search, results and settings
    functionalities"""

    def __init__(
            self,
            parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.new_connection_btn.clicked.connect(self.add_connection)
        self.edit_connection_btn.clicked.connect(self.edit_connection)
        self.remove_connection_btn.clicked.connect(self.remove_connection)
        self.connections_box.currentIndexChanged.connect(
            self.update_connection_buttons
        )
        self.update_connections_box()
        self.update_connection_buttons()
        self.connections_box.activated.connect(self.update_current_connection)
        self.pagination.setVisible(False)

        self.search_btn.clicked.connect(
            self.search_api
        )

        self.api_client = None
        self.connections_box.activated.connect(self.update_current_connection)
        self.update_current_connection(self.connections_box.currentIndex())

        settings_manager.connections_settings_updated.connect(
            self.update_connections_box
        )

    def add_connection(self):
        """ Adds a new connection into the plugin, then updates
        the connections combo box list to show the added connection.
        """
        connection_dialog = ConnectionDialog()
        connection_dialog.exec_()
        self.update_connections_box()

    def edit_connection(self):
        """ Edits the passed connection and updates the connection box list.
        """
        current_text = self.connections_box.currentText()
        if current_text == "":
            return
        connection = settings_manager.find_connection_by_name(current_text)
        connection_dialog = ConnectionDialog(connection)
        connection_dialog.exec_()
        self.update_connections_box()

    def remove_connection(self):
        """ Removes the current active connection.
        """
        current_text = self.connections_box.currentText()
        if current_text == "":
            return
        connection = settings_manager.find_connection_by_name(current_text)
        reply = QtWidgets.QMessageBox.warning(
            self,
            tr('STAC API Browser'),
            tr('Remove the connection "{}"?').format(current_text),
            QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            settings_manager.delete_connection(connection.id)
            latest_connection = settings_manager.get_latest_connection()
            settings_manager.set_current_connection(
                latest_connection.id
            ) if latest_connection is not None else None
            self.update_connections_box()

    def update_connection_buttons(self):
        """ Updates the edit and remove connection buttons state
        """
        current_name = self.connections_box.currentText()
        enabled = current_name != ""
        self.edit_connection_btn.setEnabled(enabled)
        self.remove_connection_btn.setEnabled(enabled)

    def update_current_connection(self, index: int):
        """ Sets the connection with the passed index to be the
        current selected connection.

        :param index: Index from the connection box item
        :type index: int
        """
        current_text = self.connections_box.itemText(index)
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

    def update_connections_box(self):
        """ Updates connections list displayed on the connection
        combox box to contain the latest list of the connections.
        """
        existing_connections = settings_manager.list_connections()
        self.connections_box.clear()
        if len(existing_connections) > 0:
            self.connections_box.addItems(
                conn.name for conn in existing_connections
            )
            current_connection = settings_manager.get_current_connection()
            if current_connection is not None:
                current_index = self.connections_box.\
                    findText(current_connection.name)
                self.connections_box.setCurrentIndex(current_index)
            else:
                self.connections_box.setCurrentIndex(0)

    def search_api(self):
        """ Uses the filters available on the search tab to
        search the STAC API server defined by the current connection details.
        """
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
