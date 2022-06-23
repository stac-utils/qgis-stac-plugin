# -*- coding: utf-8 -*-

"""
 Collection dialog class file
"""

import os

from qgis.PyQt import QtCore, QtGui, QtWidgets

from qgis.core import Qgis, QgsCoordinateReferenceSystem, QgsRectangle

from qgis.gui import QgsMessageBar

from ..conf import settings_manager
from ..api.client import Client
from ..utils import tr

from qgis.PyQt.uic import loadUiType

DialogUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/collection_dialog.ui")
)


class CollectionDialog(QtWidgets.QDialog, DialogUi):
    """ Dialog for displaying STAC catalog collection details"""

    def __init__(
            self,
            collection=None
    ):
        """ Constructor

        :param collection: Collection instance
        :type collection: models.Collection
        """
        super().__init__()
        self.setupUi(self)
        self.collection = collection

        self.grid_layout = QtWidgets.QGridLayout()
        self.message_bar = QgsMessageBar()
        self.prepare_message_bar()

        connection = settings_manager.get_current_connection()
        api_client = Client.from_connection_settings(connection)

        api_client.collection_received.connect(self.handle_collection)
        api_client.error_received.connect(self.handle_error)
        api_client.get_collection(collection.id)
        self.show_progress(
            tr("Fetching information for {} collection...").
            format(collection.id)
        )
        self.update_inputs(False)

    def handle_collection(self, collection):
        """ Populates the collection dialog widgets with the
        respective information from the fetchec collection

        :param collection: Fetched STAC collection
        :type collection: Collection
        """
        self.collection = collection
        if self.collection:
            self.id_le.setText(self.collection.id)
            self.title_le.setText(self.collection.title)
            if self.collection.keywords:
                self.populate_keywords(collection.keywords)
            self.description_le.setText(self.collection.description)

            if self.collection.license:
                self.license_le.setText(self.collection.license)
            if self.collection.extent:
                self.set_extent(collection.extent)

            if self.collection.links:
                self.set_links(self.collection.links)
            if self.collection.providers:
                self.set_providers(self.collection.providers)

        self.show_message(
            tr("Collection fetch has completed"),
            level=Qgis.Info
        )
        self.update_inputs(True)

    def handle_error(self, error):
        """Handles the returned response error

        :param error: Network response error
        :type error: str
        """
        self.show_message(error, level=Qgis.Critical)
        self.update_inputs(True)

    def prepare_message_bar(self):
        """ Initializes the widget message bar settings"""
        self.message_bar.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Fixed
        )
        self.grid_layout.addWidget(
            self.tab_widget,
            0, 0, 1, 1
        )
        self.grid_layout.addWidget(
            self.message_bar,
            0, 0, 1, 1,
            alignment=QtCore.Qt.AlignTop
        )
        self.layout().insertLayout(0, self.grid_layout)

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

    def update_inputs(self, enabled):
        """ Updates the inputs widgets state in the dialog.

        :param enabled: Whether to enable the inputs or disable them.
        :type enabled: bool
        """
        self.tab_widget.setEnabled(enabled)

    def populate_keywords(self, keywords):
        """ Populates the keywords list in the keyword tab

        :param keywords: List of collection keywords
        :type keywords:  []
        """
        self.keywords_table.setRowCount(0)
        for keyword in keywords:
            self.keywords_table.insertRow(self.keywords_table.rowCount())
            row = self.keywords_table.rowCount() - 1
            item = QtWidgets.QTableWidgetItem(keyword)
            self.keywords_table.setItem(row, 0, item)

    def set_extent(self, extent):
        """ Sets the collection spatial and temporal extents

        :param extent: Instance that contain spatial and temporal extents
        :type extent: models.Extent
        """
        spatial_extent = extent.spatial
        if spatial_extent:
            self.spatialExtentSelector.setOutputCrs(
                QgsCoordinateReferenceSystem("EPSG:4326")
            )

            bbox = spatial_extent.bbox[0] \
                if spatial_extent.bbox and isinstance(spatial_extent.bbox, list) \
                else None

            original_extent = QgsRectangle(
                bbox[0],
                bbox[1],
                bbox[2],
                bbox[3]
            ) if bbox and isinstance(bbox, list) else QgsRectangle()
            self.spatialExtentSelector.setOriginalExtent(
                original_extent,
                QgsCoordinateReferenceSystem("EPSG:4326")
            )
            self.spatialExtentSelector.setOutputExtentFromOriginal()

        temporal_extents = extent.temporal
        if temporal_extents:
            pass
        else:
            self.from_date.clear()
            self.to_date.clear()

    def set_links(self, links):
        """ Populates the links list in the link tab

        :param links: List of collection links
        :type links:  []
        """
        self.links_table.setRowCount(0)
        for link in links:
            self.links_table.insertRow(self.links_table.rowCount())
            row = self.links_table.rowCount() - 1
            self.links_table.setItem(
                row,
                0,
                QtWidgets.QTableWidgetItem(link.title)
            )
            self.links_table.setItem(
                row,
                1,
                QtWidgets.QTableWidgetItem(link.href)
            )
            self.links_table.setItem(
                row,
                2,
                QtWidgets.QTableWidgetItem(link.type)
            )
            self.links_table.setItem(
                row,
                3,
                QtWidgets.QTableWidgetItem(link.rel)
            )

    def set_providers(self, providers):
        """ Populates the providers list in the providers tab

        :param providers: List of collection providers
        :type providers:  []
        """
        self.providers_table.setRowCount(0)
        for provider in providers:
            self.providers_table.insertRow(self.providers_table.rowCount())
            row = self.providers_table.rowCount() - 1
            self.providers_table.setItem(
                row,
                0,
                QtWidgets.QTableWidgetItem(provider.name)
            )
            self.providers_table.setItem(
                row,
                1,
                QtWidgets.QTableWidgetItem(provider.description)
            )
            self.providers_table.setItem(
                row,
                2,
                QtWidgets.QTableWidgetItem(str(provider.roles))
            )
            self.providers_table.setItem(
                row,
                3,
                QtWidgets.QTableWidgetItem(provider.url)
            )
