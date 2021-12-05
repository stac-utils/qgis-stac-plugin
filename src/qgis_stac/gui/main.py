import os

from qgis.PyQt import (
    QtCore,
    QtGui,
    QtNetwork,
    QtWidgets,
    QtXml,
)
from qgis.PyQt.uic import loadUiType

from qgis.core import Qgis, QgsCoordinateReferenceSystem
from qgis.gui import QgsMessageBar
from qgis.utils import iface

from ..resources import *
from ..gui.connection_dialog import ConnectionDialog

from ..conf import settings_manager
from ..api.models import ItemSearch, ResourceType
from ..api.client import Client

from ..utils import tr

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/qgis_stac_widget.ui")
)


class QgisStacWidget(QtWidgets.QWidget, WidgetUi):
    """ Main plugin widget that contains tabs for search, results and settings
    functionalities"""

    search_started = QtCore.pyqtSignal()
    search_completed = QtCore.pyqtSignal()

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

        self.search_btn.clicked.connect(
            self.search_api
        )

        self.fetch_collections_btn.clicked.connect(
            self.search_collections
        )

        self.api_client = None
        self.connections_box.activated.connect(self.update_current_connection)
        self.update_current_connection(self.connections_box.currentIndex())

        settings_manager.connections_settings_updated.connect(
            self.update_connections_box
        )

        self.search_type = ResourceType.FEATURE

        self.search_started.connect(self.handle_search_start)
        self.search_completed.connect(self.handle_search_end)

        # self.collections_tree.itemDoubleClicked.connect(self.show_collection_info)

        self.grid_layout = QtWidgets.QGridLayout()
        self.message_bar = QgsMessageBar()
        self.prepare_message_bar()

        self.prepare_extent_box()

        # prepare sort and filter model for the collections
        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Title'])
        self.proxy_model = QtCore.QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setDynamicSortFilter(True)
        self.proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.collections_tree.setModel(self.proxy_model)

        self.filter_text.textChanged.connect(self.filter_changed)
        self.collections_tree.selectionModel().\
            selectionChanged.connect(
            self.collection_selection_changed
        )

        # prepare sort and filter model for the searched items
        self.items_model = QtGui.QStandardItemModel()
        self.items_model.setHorizontalHeaderLabels(['Id'])
        self.items_proxy_model = QtCore.QSortFilterProxyModel()
        self.items_proxy_model.setSourceModel(self.items_model)
        self.items_proxy_model.setDynamicSortFilter(True)
        self.items_proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.items_tree.setModel(self.items_proxy_model)

        # initialize page

        self.page = 1

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
        self.api_client.collections_received.connect(self.display_results)
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

    def previous_items(self):
        self.page -= 1
        self.search_api()

    def next_items(self):
        self.page += 1
        self.search_api()

    def search_api(self):
        """ Uses the filters available on the search tab to
        search the STAC API server defined by the current connection details.
        Emits the search started signal to alert UI about the
        search operation.
        """
        self.search_type = ResourceType.FEATURE

        start_dte = self.start_dte.dateTime() \
            if self.date_filter_group.isChecked() else None
        end_dte = self.end_dte.dateTime() \
            if self.date_filter_group.isChecked() else None

        collections = self.get_selected_collections()
        page_size = settings_manager.get_current_connection().page_size
        self.api_client.get_items(
            ItemSearch(
                collections=collections,
                page_size=page_size,
                start_datetime=start_dte,
                end_datetime=end_dte,
            )
        )
        self.search_started.emit()

    def search_collections(self):
        """ Searches for the collections available on the
        """
        self.search_type = ResourceType.COLLECTION

        self.api_client.get_collections()
        self.search_started.emit()

    def show_progress(self, message):
        message_bar_item = self.message_bar.createMessage(message)
        progress_bar = QtWidgets.QProgressBar()
        progress_bar.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(0)
        message_bar_item.layout().addWidget(progress_bar)
        self.message_bar.pushWidget(message_bar_item, Qgis.Info)

    def handle_search_start(self):
        self.message_bar.clearWidgets()
        self.show_progress("Searching...")
        self.update_search_inputs(enabled=False)

    def handle_search_end(self):
        self.message_bar.clearWidgets()
        self.update_search_inputs(enabled=True)

    def update_search_inputs(self, enabled):
        self.connections_group.setEnabled(enabled)
        self.date_filter_group.setEnabled(enabled)
        self.extent_box.setEnabled(enabled)
        self.metadata_group.setEnabled(enabled)
        self.search_btn.setEnabled(enabled)

    def prepare_message_bar(self):
        self.message_bar.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Fixed
        )
        self.grid_layout.addWidget(
            self.container,
            0, 0, 1, 1
        )
        self.grid_layout.addWidget(
            self.message_bar,
            0, 0, 1, 1,
            alignment=QtCore.Qt.AlignTop
        )
        self.layout().insertLayout(0, self.grid_layout)

    def prepare_extent_box(self):
        self.extent_box.setOutputCrs(
            QgsCoordinateReferenceSystem("EPSG:4326")
        )
        map_canvas = iface.mapCanvas()
        self.extent_box.setCurrentExtent(
            map_canvas.mapSettings().destinationCrs().bounds(),
            map_canvas.mapSettings().destinationCrs()
        )
        self.extent_box.setOutputExtentFromCurrent()
        self.extent_box.setMapCanvas(map_canvas)

    def display_results(self, results):
        if self.search_type == ResourceType.COLLECTION:
            self.model.removeRows(0, self.model.rowCount())
            for result in results:
                item = QtGui.QStandardItem(result.title)
                item.setData(result.id, 1)
                self.model.appendRow(item)

            self.proxy_model.setSourceModel(self.model)

        elif self.search_type == ResourceType.FEATURE:
            self.items_model.removeRows(0, self.items_model.rowCount())
            for result in results:
                item = QtGui.QStandardItem(result.id)
                self.items_model.appendRow(item)

            self.items_proxy_model.setSourceModel(self.items_model)
            self.container.setCurrentIndex(1)
        else:
            raise NotImplementedError
        self.search_completed.emit()

    def display_search_error(self, message):
        self.message_bar.clearWidgets()
        self.show_message(message, level=Qgis.Critical)
        self.search_completed.emit()

    def collection_selection_changed(self, selected, deselected):
        collections = self.selected_collections.text()
        for index in deselected.indexes():
            collections = collections.replace(f"{index.data(1)},", "")
        for index in selected.indexes():
            collections += f"{index.data(1)},"
        self.selected_collections.setText(collections)

    def filter_changed(self, filter_text):
        exp_reg = QtCore.QRegExp(
            filter_text,
            QtCore.Qt.CaseInsensitive,
            QtCore.QRegExp.FixedString
        )
        self.proxy_model.setFilterRegExp(exp_reg)

    def get_selected_collections(self):
        indexes = self.collections_tree.selectionModel().selectedIndexes()
        collections_ids = []

        for index in indexes:
            collections_ids.append(index.data(1))

        return collections_ids
