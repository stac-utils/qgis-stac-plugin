# -*- coding: utf-8 -*-

"""
 The plugin main window class file
"""

import os

from functools import partial

from qgis.PyQt import (
    QtCore,
    QtGui,
    QtNetwork,
    QtWidgets,
    QtXml,
)
from qgis.PyQt.uic import loadUiType

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsTask
)
from qgis.gui import QgsMessageBar
from qgis.utils import iface

from ..resources import *

from ..gui.connection_dialog import ConnectionDialog
from ..gui.collection_dialog import CollectionDialog
from ..gui.queryable_property import QueryablePropertyWidget

from ..conf import ConnectionSettings, Settings, settings_manager

from ..api.models import (
    FilterLang,
    ItemSearch,
    ResourceType,
    SearchFilters,
    SortField,
    SortOrder,
    QueryableFetchType
)
from ..api.client import Client

from .result_item_model import ItemsModel, ItemsSortFilterProxyModel
from .json_highlighter import JsonHighlighter

from ..utils import (
    open_folder,
    log,
    tr,
)

from .result_item_widget import add_footprint_helper, ResultItemWidget

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/qgis_stac_main.ui")
)


class QgisStacWidget(QtWidgets.QMainWindow, WidgetUi):
    """ Main plugin UI that contains tabs for search, results and settings
    functionalities"""

    search_started = QtCore.pyqtSignal()
    search_completed = QtCore.pyqtSignal()
    updated_result_items = QtCore.pyqtSignal(ConnectionSettings, list)
    items_refresh_finished = QtCore.pyqtSignal()

    result_items = []

    def __init__(
            self,
            parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)

        self.new_connection_btn.clicked.connect(self.add_connection)
        self.edit_connection_btn.clicked.connect(self.edit_connection)
        self.remove_connection_btn.clicked.connect(self.remove_connection)

        self.updated_result_items.connect(self.update_refreshed_items)

        self.connections_box.currentIndexChanged.connect(
            self.update_connection_buttons
        )

        self.footprint_items = {}
        self.footprint_btn.clicked.connect(
            self.footprint_btn_clicked
        )
        self.all_footprints_btn.clicked.connect(
            self.all_footprints_btn_clicked
        )
        self.all_footprints_btn.setEnabled(
            len(self.result_items) > 0
        )

        self.search_btn.clicked.connect(
            self.search_items_api
        )
        self.next_btn.clicked.connect(
            self.next_items
        )
        self.prev_btn.clicked.connect(
            self.previous_items
        )
        self.clear_results_btn.clicked.connect(
            self.clear_search_results
        )

        self.fetch_collections_btn.clicked.connect(
            self.fetch_collections
        )
        self.update_current_connection(self.connections_box.currentIndex())
        settings_manager.connections_settings_updated.connect(
            self.update_connections_box
        )
        settings_manager.connections_settings_updated.connect(
            self.update_api_client
        )

        self.update_api_client()

        self.search_type = ResourceType.FEATURE
        self.current_progress_message = tr("Searching...")

        self.search_started.connect(self.handle_search_start)
        self.search_completed.connect(self.handle_search_end)

        self.grid_layout = QtWidgets.QGridLayout()
        self.message_bar = QgsMessageBar()
        self.progress_bar = None
        self.prepare_message_bar()

        self.prepare_extent_box()

        # prepare sort and filter model for the collections
        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Title'])
        self.proxy_model = QtCore.QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setDynamicSortFilter(True)
        self.proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.collections_tree.setModel(self.proxy_model)
        self.collections_tree.selectionModel().selectionChanged.connect(
            self.display_selected_collection
        )
        self.collections_tree.doubleClicked.connect(self.collections_tree_double_clicked)

        self.filter_text.textChanged.connect(self.filter_changed)

        self.update_connections_box()
        self.update_connection_buttons()
        self.connections_box.activated.connect(self.update_current_connection)

        self.search_error_message = None

        # initialize page
        self.page = 1
        self.total_pages = 0

        self.current_collections = []

        self.highlighter = None
        self.prepare_filter_box()

        # actions that trigger saving filters to the plugin settings

        self.start_dte.valueChanged.connect(self.save_filters)
        self.end_dte.valueChanged.connect(self.save_filters)
        self.extent_box.extentChanged.connect(self.save_filters)
        self.date_filter_group.toggled.connect(self.save_filters)
        self.advanced_box.toggled.connect(self.save_filters)
        self.extent_box.toggled.connect(self.save_filters)
        self.filter_lang_cmb.activated.connect(self.save_filters)
        self.filter_edit.textChanged.connect(self.save_filters)
        self.sort_cmb.activated.connect(self.save_filters)
        self.reverse_order_box.toggled.connect(self.save_filters)

        self.populate_sorting_field()

        download_folder = settings_manager.get_value(
            Settings.DOWNLOAD_FOLDER
        )
        self.download_folder_btn.setFilePath(
            download_folder
        ) if download_folder else None

        self.download_folder_btn.fileChanged.connect(
            self.save_download_folder)
        self.open_folder_btn.clicked.connect(self.open_download_folder)

        # setup model for filtering and sorting item results

        self.item_model = ItemsModel([])
        self.items_proxy_model = ItemsSortFilterProxyModel()
        self.items_proxy_model.setSourceModel(self.item_model)
        self.items_proxy_model.setDynamicSortFilter(True)
        self.items_proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.items_filter.textChanged.connect(self.items_filter_changed)

        self.get_filters()
        self.prepare_plugin_settings()

        self.populate_queryable_field()

        self.fetch_queryable_btn.clicked.connect(self.fetch_queryable)
        self.clear_properties_btn.clicked.connect(self.clear_properties)

        self.queryable_property_widgets = []
        self.queryable_properties = []

    def prepare_plugin_settings(self):
        """ Initializes all the plugin related settings"""

        auto_asset_loading = settings_manager.get_value(
            Settings.AUTO_ASSET_LOADING,
            False,
            setting_type=bool
        )
        self.asset_loading.setChecked(auto_asset_loading)

        self.asset_loading.toggled.connect(self.update_plugin_settings)
        self.asset_loading.stateChanged.connect(self.update_plugin_settings)

    def update_plugin_settings(self):
        """ Makes updates to all the plugin settings
         defined in the settings tab.
         """
        settings_manager.set_value(
            Settings.AUTO_ASSET_LOADING,
            self.asset_loading.isChecked(),
        )

    def prepare_filter_box(self):
        """ Prepares the advanced filter group box inputs
        """

        labels = {
            FilterLang.CQL_JSON: tr("CQL_JSON"),
            FilterLang.CQL2_JSON: tr("CQL2_JSON"),
            FilterLang.STAC_QUERY: tr("STAC_QUERY"),
        }
        for lang_type, item_text in labels.items():
            self.filter_lang_cmb.addItem(item_text, lang_type)

        self.filter_lang_cmb.setCurrentIndex(
            self.filter_lang_cmb.findData(
                FilterLang.CQL_JSON,
                role=QtCore.Qt.UserRole)
        )

        self.highlighter = JsonHighlighter(self.filter_edit.document())
        self.filter_edit.cursorPositionChanged.connect(
            self.highlighter.rehighlight)

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
        current_connection = settings_manager. \
            find_connection_by_name(current_text)
        settings_manager.set_current_connection(current_connection.id)
        if current_connection:
            self.update_api_client()
            # Update the collections view to show the current connection
            # collections
            collections = settings_manager.get_collections(
                current_connection.id
            )
            self.model.removeRows(0, self.model.rowCount())
            self.load_collections(collections)
            # self.handle_queryable(Queryable())

        self.search_btn.setEnabled(current_connection is not None)

    def clear_properties(self):
        """ Removes all the current queryable properties from the
        queryable group box
        """

        self.queryable_properties = []
        self.queryable_property_widgets = []
        self.queryable_area.setWidget(QtWidgets.QWidget())

    def fetch_queryable(self):
        """ Gets the queryable property using the plugin API."""
        self.current_progress_message = tr(
            "Fetching queryable properties..."
        )
        self.clear_properties()
        self.search_started.emit()

        queryable_fetch_type = self.queryable_fetch_cmb.itemData(
            self.queryable_fetch_cmb.currentIndex()
        )

        if queryable_fetch_type == QueryableFetchType.COLLECTION:
            for collection in self.get_selected_collections():
                try:
                    QgsTask.fromFunction(
                        'Queryable plugin API function',
                        self.api_client.get_queryable(
                            fetch_type=queryable_fetch_type,
                            resource=collection
                        )
                    )
                except Exception as err:
                    log(tr("Error in getting queryables properties for"
                           " {}, {}".
                           format(collection, err))
                        )
            if not self.get_selected_collections():
                self.show_message(
                    tr("No collection has been selected"),
                    level=Qgis.Info
                )
                self.update_search_inputs(True)

        else:
            self.api_client.get_queryable(
                fetch_type=queryable_fetch_type
            )

    def handle_queryable(self, queryable):
        """ Adds response queryable properties from the plugin API to the
        plugin UI.

        :param queryable: Queryable properties
        :type queryable: Queryable
        """

        scroll_container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(1)

        scroll_container.setLayout(layout)

        # Combine current properties with new properties
        # while removing duplicates

        self.queryable_properties.extend(
            queryable for queryable in queryable.properties
            if queryable not in self.queryable_properties
        )

        for property in self.queryable_properties:
            property_widget = QueryablePropertyWidget(
                property
            )
            layout.addWidget(property_widget)
            layout.setAlignment(property_widget, QtCore.Qt.AlignTop)
            self.queryable_property_widgets.append(property_widget)

        self.queryable_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.queryable_area.setWidgetResizable(True)
        self.queryable_area.setWidget(scroll_container)

        if len(queryable.properties) < 0:
            label = QtWidgets.QLabel(tr("No queryable properties found."))
            layout.addWidget(label)

        self.search_completed.emit()

    def update_api_client(self):
        """
        Updates the api client for the current active connection

        """
        current_connection = settings_manager.get_current_connection()
        if current_connection:
            self.api_client = Client.from_connection_settings(
                current_connection
            )
            if self.api_client:
                self.api_client.items_received.connect(self.display_results)
                self.api_client.collections_received.connect(self.display_results)
                self.api_client.queryable_received.connect(self.handle_queryable)
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
                current_index = self.connections_box. \
                    findText(current_connection.name)
                self.connections_box.setCurrentIndex(current_index)
                # Update the collections view to show the current connection
                # collections
                collections = settings_manager.get_collections(
                    current_connection.id
                )
                self.model.removeRows(0, self.model.rowCount())
                self.load_collections(collections)
            else:
                self.connections_box.setCurrentIndex(0)

    def search_items_api(self):
        """ Sets the current progress message, initiliaze search page
        and calls the plugin function for searching current catalog items.
        """
        self.current_progress_message = tr(
            "Searching items..."
        )
        self.page = 1
        self.search_items()

    def previous_items(self):
        """ Sets the items search to go on the previous page.
        """
        self.page -= 1
        self.current_progress_message = tr(
            "Retrieving previous page..."
        )
        self.search_items()

    def next_items(self):
        """ Sets the items search to go on the next page.
       """
        self.page += 1
        self.current_progress_message = tr(
            "Retrieving next page..."
        )
        self.search_items()

    def search_items(self):
        """ Uses the filters available on the search tab to
        search the STAC Catalog defined by the current connection details.
        Emits the search started signal to alert UI about the
        search operation.
        """
        self.search_type = ResourceType.FEATURE
        use_start_date = self.date_filter_group.isChecked() and \
                         not self.start_dte.dateTime().isNull()
        use_end_date = self.date_filter_group.isChecked() and \
                       not self.end_dte.dateTime().isNull()
        start_dte = self.start_dte.dateTime() \
            if use_start_date else None
        end_dte = self.end_dte.dateTime() \
            if use_end_date else None

        collections = self.get_selected_collections()
        page_size = settings_manager.get_current_connection().page_size
        spatial_extent = self.extent_box.outputExtent() \
            if self.extent_box.isChecked() else None

        filter_text = self.filter_edit.toPlainText() \
            if self.advanced_box.isChecked() else None
        filter_lang = self.filter_lang_cmb.itemData(
            self.filter_lang_cmb.currentIndex()
        ) if self.advanced_box.isChecked() else None

        if self.queryable_box.isChecked():
            filter_texts = []
            for property_widget in self.queryable_property_widgets:
                filter_texts.append(property_widget.filter_text()) \
                if property_widget.filter_text() else None
            filter_text = ' and '.join(filter_texts)
            filter_lang = FilterLang.CQL2_TEXT

        sort_field = self.sort_cmb.itemData(
            self.sort_cmb.currentIndex()
        )

        sort_order = SortOrder.DESCENDING \
            if self.reverse_order_box.isChecked() else SortOrder.ASCENDING

        self.api_client.get_items(
            ItemSearch(
                collections=collections,
                page_size=page_size,
                page=self.page,
                start_datetime=start_dte,
                end_datetime=end_dte,
                spatial_extent=spatial_extent,
                filter_text=filter_text,
                filter_lang=filter_lang,
                sortby=sort_field,
                sort_order=sort_order,
            )
        )
        self.search_started.emit()

    def fetch_collections(self):
        """ Fetches the collections available on the current
            STAC API connection.
        """
        self.search_type = ResourceType.COLLECTION
        self.current_progress_message = tr("Fetching collections...")

        self.api_client.get_collections()
        self.search_started.emit()

    def show_message(
            self,
            message,
            level=Qgis.Warning
    ):
        """ Shows message on the main widget message bar

        :param message: Message text
        :type message: str

        :param level: Message level type
        :type level: Qgis.MessageLevel
        """
        self.message_bar.clearWidgets()
        self.message_bar.pushMessage(message, level=level)

    def show_progress(self, message, minimum=0, maximum=0):
        """ Shows the progress message on the main widget message bar

        :param message: Progress message
        :type message: str

        :param minimum: Minimum value that can be set on the progress bar
        :type minimum: int

        :param maximum: Maximum value that can be set on the progress bar
        :type maximum: int
        """
        self.message_bar.clearWidgets()
        message_bar_item = self.message_bar.createMessage(message)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.progress_bar.setMinimum(minimum)
        self.progress_bar.setMaximum(maximum)
        message_bar_item.layout().addWidget(self.progress_bar)
        self.message_bar.pushWidget(message_bar_item, Qgis.Info)

    def update_progress_bar(self, value):
        """Sets the value of the progress bar

        :param value: Value to be set on the progress bar
        :type value: float
        """
        if self.progress_bar:
            try:
                self.progress_bar.setValue(int(value))
            except RuntimeError:
                log(
                    tr("Error setting value to a progress bar"),
                    notify=False
                )

    def handle_search_start(self):
        """ Handles the logic to be executed when searching has started"""
        self.message_bar.clearWidgets()
        self.show_progress(self.current_progress_message)
        self.update_search_inputs(enabled=False)

    def handle_search_end(self):
        """ Handles the logic to be executed when searching has ended"""
        self.message_bar.clearWidgets()
        if self.search_error_message:
            self.show_message(self.search_error_message, Qgis.Critical)
            self.search_error_message = None
        self.update_search_inputs(enabled=True)

    def update_search_inputs(self, enabled):
        """ Sets the search inputs state using the provided enabled status

        :param enabled: Whether to enable the widgets.
        :type enabled: bool
        """
        self.connections_group.setEnabled(enabled)
        self.collections_group.setEnabled(enabled)
        self.date_filter_group.setEnabled(enabled)
        self.extent_box.setEnabled(enabled)
        self.advanced_box.setEnabled(enabled)
        self.queryable_box.setEnabled(enabled)
        self.search_btn.setEnabled(enabled)
        self.sort_by_la.setEnabled(enabled)
        self.sort_cmb.setEnabled(enabled)
        self.reverse_order_box.setEnabled(enabled)

    def prepare_message_bar(self):
        """ Initializes the widget message bar settings"""
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
        self.central_widget.layout().insertLayout(0, self.grid_layout)

    def prepare_extent_box(self):
        """ Configure the spatial extent box with the initial settings. """
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
        self.extent_box.setChecked(False)

    def display_selected_collection(self):
        """ Shows the current selected collections in the
        targeted label
        """
        collections = self.get_selected_collections(title=True)

        self.selected_collections_la.setText(
            tr("Selected collections: <b>{}</b>").format(
                ', '.join(collections)
            )
        )

    def collections_tree_double_clicked(self, index):
        """ Opens the collection dialog when an entry from the
        collections view tree has been double clicked.

        :param index: Index of the double clicked item.
        :type index: int

        """
        collection = self.collections_tree.model().data(index, 1)
        collection_dialog = CollectionDialog(collection)
        collection_dialog.exec_()

    def display_results(self, results, pagination=None):
        """ Shows the found results into their respective view. Emits
        the search end signal after completing loading up the results
        into the view.

        :param results: Search results
        :return: list

        :param pagination: Pagination details
        :type pagination: ResourcePagination
        """
        if self.search_type == ResourceType.COLLECTION:
            self.model.removeRows(0, self.model.rowCount())
            self.current_collections = results
            self.load_collections(results)
            self.save_filters(collections=self.current_collections)

        elif self.search_type == ResourceType.FEATURE:

            if pagination and pagination.total_pages > 0:
                if self.page > 1:
                    self.page -= 1
                self.next_btn.setEnabled(False)
            else:
                if len(results) > 0:
                    self.result_items_la.setText(
                        tr(
                            "Displaying page {} of results, {} item(s)"
                        ).format(
                            self.page,
                            len(results)
                        )
                    )
                    self.item_model = ItemsModel(results)
                    self.items_proxy_model.setSourceModel(self.item_model)
                    settings_manager.delete_all_items(
                        settings_manager.get_current_connection(),
                        self.page
                    )
                    self.populate_results(results)
                else:

                    self.clear_search_results()
                    if self.page > 1:
                        self.page -= 1
                    if self.date_filter_group.isChecked() \
                            or self.extent_box.isChecked():
                        self.result_items_la.setText(
                            tr(
                                "No items were found, "
                                "try to expand the date filter or "
                                "the spatial extent filter used."
                            )
                        )
                    else:
                        self.result_items_la.setText(
                            tr(
                                "No items were found"
                            )
                        )
                self.next_btn.setEnabled(len(results) > 0)
                self.prev_btn.setEnabled(self.page > 1)
                self.footprint_btn.setEnabled(
                    False
                )
                self.all_footprints_btn.setEnabled(
                    len(self.result_items) > 0
                )
                self.footprint_items = {}
            self.container.setCurrentIndex(1)

        else:
            raise NotImplementedError
        self.search_completed.emit()

    def display_search_error(self, message):
        """
        Shows the search error message.
        Sets the search error message and
        emits search_completed signal that alerts the search end handler to
        display the search error message.

        :param message: search error message.
        :type message: str
        """
        self.message_bar.clearWidgets()
        self.search_error_message = message
        self.search_completed.emit()

    def update_refreshed_items(self, connection, items):
        """ Refreshes the current SAS token connection results items """

        if connection == settings_manager.get_current_connection():
            self.display_results(items)

    def populate_results(self, results):
        """ Add the found results into the widget scroll area.

        :param results: List of items results
        :type results: list
        """

        self.result_items = results
        scroll_container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(1)
        for result in results:
            search_result_widget = ResultItemWidget(
                result,
                main_widget=self,
                parent=self
            )
            footprint_selected_partial = partial(
                self.footprint_selected,
                result
            )
            footprint_deselected_partial = partial(
                self.footprint_deselected,
                result
            )
            search_result_widget.footprint_selected.connect(
                footprint_selected_partial
            )
            search_result_widget.footprint_deselected.connect(
                footprint_deselected_partial
            )

            layout.addWidget(search_result_widget)
            layout.setAlignment(search_result_widget, QtCore.Qt.AlignTop)
        vertical_spacer = QtWidgets.QSpacerItem(
            20,
            40,
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding
        )
        layout.addItem(vertical_spacer)
        scroll_container.setLayout(layout)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(scroll_container)

    def footprint_selected(self, item):
        """ Adds the passed item to the list of the
        footprints to be added.
        """
        self.footprint_items[item.id] = item
        self.footprint_btn.setText(
            f"Add the selected footprint(s) ({len(self.footprint_items.items())})"
        )
        self.footprint_btn.setEnabled(
            len(self.footprint_items.items()) > 0
        )

    def footprint_deselected(self, item):
        """ Removes the passed item from the  list of the
        footprints to be added.
        """
        self.footprint_items.pop(item.id)
        self.footprint_btn.setText(
            f"Add the selected footprint(s) ({len(self.footprint_items.items())})"
        ) if self.footprint_items else \
            self.footprint_btn.setText(
                "Add the selected footprint(s)"
            )
        self.footprint_btn.setEnabled(
            len(self.footprint_items.items()) > 0
        )

    def footprint_btn_clicked(self):
        """ Adds selected footprints as map layers."""
        for key, item in self.footprint_items.items():
            try:
                footprint_task = QgsTask.fromFunction(
                    'Add footprints',
                    add_footprint_helper(item, self)
                )
                QgsApplication.taskManager().addTask(footprint_task)
            except Exception as err:
                log(
                    tr("Error loading item footprint {}, {}".
                       format(item.id, err))
                )

    def all_footprints_btn_clicked(self):
        """ Adds all footprints for the current page items as map layers."""
        for item in self.result_items:
            try:
                footprint_task = QgsTask.fromFunction(
                    'Add footprint',
                    add_footprint_helper(item, self)
                )
                QgsApplication.taskManager().addTask(footprint_task)
            except Exception as err:
                log(
                    tr("Error loading item footprint {}, {}".
                       format(item.id, err))
                )

    def clear_search_results(self):
        """ Clear current search results from the UI"""
        self.scroll_area.setWidget(QtWidgets.QWidget())
        self.result_items_la.clear()
        self.result_items = []

    def filter_changed(self, filter_text):
        """
        Sets the filter on the collections proxy model and trigger
        filter action on the model.

        :param filter_text: Filter text
        :type: str
        """
        exp_reg = QtCore.QRegExp(
            filter_text,
            QtCore.Qt.CaseInsensitive,
            QtCore.QRegExp.FixedString
        )
        self.proxy_model.setFilterRegExp(exp_reg)

    def items_filter_changed(self, filter_text):
        """
        Sets the filter on the items proxy model and trigger
        filter action on the model.

        :param filter_text: Filter text
        :type: str
        """
        # TODO update to use QtCore.QRegExp, QRegularExpression will be
        # deprecated.
        options = QtCore.QRegularExpression.NoPatternOption
        options |= QtCore.QRegularExpression.CaseInsensitiveOption
        regular_expression = QtCore.QRegularExpression(filter_text, options)
        self.items_proxy_model.setFilterRegularExpression(regular_expression)

        filtered_data = []
        for index in range(0, self.items_proxy_model.rowCount()):
            model_index = self.items_proxy_model.index(index, 0)
            filtered_data.append(self.items_proxy_model.data(model_index))

        self.populate_results(filtered_data)

    def populate_sorting_field(self):
        """" Initializes sorting field combo box list items"""
        labels = {
            SortField.ID: tr("Name"),
            SortField.COLLECTION: tr("Collection"),
        }
        self.sort_cmb.addItem("")
        for ordering_type, item_text in labels.items():
            self.sort_cmb.addItem(item_text, ordering_type)
        self.sort_cmb.setCurrentIndex(0)

    def populate_queryable_field(self):
        """" Initializes queryable field combo box list items"""
        labels = {
            QueryableFetchType.CATALOG: tr("Fetch from Catalog"),
            QueryableFetchType.COLLECTION:
                tr("Fetch from current selected collections"),
        }
        for queryable_type, item_text in labels.items():
            self.queryable_fetch_cmb.addItem(item_text, queryable_type)
        self.queryable_fetch_cmb.setCurrentIndex(0)

    def get_selected_collections(self, title=False):
        """ Gets the currently selected collections from the collection
        view.

        :param title: Whether to return collection titles or ids
        :type title: bool

        :returns: Collection
        :rtype: list
        """
        data_index = 1
        indexes = self.collections_tree.selectionModel().selectedIndexes()
        collections_items = []

        for index in indexes:
            collection = index.data(data_index)
            item = collection.title if title else collection.id
            collections_items.append(item)

        return collections_items

    def load_collections(self, collections):
        """ Adds the collections results into collections tree view

        :param collections: List of collections to be added
        :type collections: []
        """
        self.model.removeRows(0, self.model.rowCount())

        self.result_collections_la.setText(
            tr("{} STAC collection(s)").format(
                len(collections)
            )
        )

        for result in collections:
            title = result.title if result.title else tr("No Title") + f" ({result.id})"
            item = QtGui.QStandardItem(title)
            item.setData(result, 1)
            self.model.appendRow(item)

        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.sort(QtCore.Qt.DisplayRole)

    def save_download_folder(self, folder):
        """ Saves the passed folder into the plugin settings

        :param folder: Folder intended to be saved
        :type folder: str
        """
        if folder:
            try:
                if not os.path.exists(folder):
                    os.makedirs(folder)

                settings_manager.set_value(
                    Settings.DOWNLOAD_FOLDER,
                    str(folder)
                )
            except PermissionError:
                self.show_message(
                    tr("Unable to write to {} due to permissions. "
                       "Choose a different folder".format(
                        folder)
                    ),
                    level=Qgis.Critical
                )
        else:
            settings_manager.set_value(
                Settings.DOWNLOAD_FOLDER,
                folder
            )
            self.show_message(
                tr(
                    'Download folder has not been set, '
                    'a system temporary folder will be used'
                ),
                level=Qgis.Warning
            )

    def open_download_folder(self):
        """ Opens the current download folder"""
        result = open_folder(
            self.download_folder_btn.filePath()
        )

        if not result[0]:
            self.show_message(result[1], level=Qgis.Critical)

    def save_filters(self, collections=None):
        """ Save search filters fetched from the corresponding UI inputs """
        filter_lang = self.filter_lang_cmb.itemData(
            self.filter_lang_cmb.currentIndex()
        )
        collections = collections if isinstance(collections, list) else None

        sort_field = self.sort_cmb.itemData(
            self.sort_cmb.currentIndex()
        )
        sort_order = SortOrder.DESCENDING if self.reverse_order_box.isChecked() \
            else SortOrder.ASCENDING

        filters = SearchFilters(
            collections=collections,
            start_date=(
                self.start_dte.dateTime()
                if not self.start_dte.dateTime().isNull() else None

            ),
            end_date=(
                self.end_dte.dateTime()
                if not self.end_dte.dateTime().isNull() else None
            ),
            spatial_extent=self.extent_box.outputExtent(),
            date_filter=self.date_filter_group.isChecked(),
            spatial_extent_filter=self.extent_box.isChecked(),
            advanced_filter=self.advanced_box.isChecked(),
            filter_lang=filter_lang,
            filter_text=self.filter_edit.toPlainText(),
            sort_field=sort_field,
            sort_order=sort_order,
        )
        settings_manager.save_search_filters(filters)

    def get_filters(self):
        """ Get the store search filters and load the into their
        respectively UI components
        """

        filters = settings_manager.get_search_filters()
        if filters.collections:
            self.load_collections(filters.collections)
        if filters.start_date is not None:
            self.start_dte.setDateTime(
                filters.start_date
            )
        else:
            self.start_dte.setDateTime(
                QtCore.QDateTime()
            )
        if filters.end_date is not None:
            self.end_dte.setDateTime(
                filters.end_date
            )
        else:
            self.end_dte.setDateTime(
                QtCore.QDateTime()
            )
        if filters.spatial_extent is not None:
            self.extent_box.setOutputExtentFromUser(
                filters.spatial_extent,
                QgsCoordinateReferenceSystem("EPSG:4326"),
            )
        self.date_filter_group.setChecked(filters.date_filter)
        self.extent_box.setChecked(filters.spatial_extent_filter)
        self.advanced_box.setChecked(filters.advanced_filter)
        self.filter_lang_cmb.setCurrentIndex(
            self.filter_lang_cmb.findData(
                filters.filter_lang,
                role=QtCore.Qt.UserRole
            )
        ) if filters.filter_lang else None
        self.filter_edit.setPlainText(filters.filter_text)

        self.sort_cmb.setCurrentIndex(
            self.sort_cmb.findData(
                filters.sort_field,
                role=QtCore.Qt.UserRole
            )
        ) if filters.sort_field else None
        self.reverse_order_box.setChecked(
            filters.sort_order == SortOrder.DESCENDING
        )
