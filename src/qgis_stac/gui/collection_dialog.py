import os

from qgis.PyQt import QtCore, QtGui, QtWidgets

from qgis.core import QgsCoordinateReferenceSystem, QgsRectangle


from qgis.PyQt.uic import loadUiType

DialogUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/collection_dialog.ui")
)


class CollectionDialog(QtWidgets.QDialog, DialogUi):
    """ Dialog for displaying STAC catalog collections details"""

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

    def populate_keywords(self, keywords):
        self.keywords_table.setRowCount(0)
        for keyword in keywords:
            self.keywords_table.insertRow(self.keywords_table.rowCount())
            row = self.keywords_table.rowCount() - 1
            item = QtWidgets.QTableWidgetItem(keyword)
            self.keywords_table.setItem(row, 0, item)

    def set_extent(self, extent):
        spatial_extent = extent.spatial
        if spatial_extent:
            self.spatialExtentSelector.setOutputCrs(
                QgsCoordinateReferenceSystem("EPSG:4326")
            )
            original_extent = QgsRectangle()
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

        self.links_table.setRowCount(0)
        for link in links:
            self.links_table.insertRow(self.links_table.rowCount())
            row = self.links_table.rowCount() - 1
            self.links_table.setItem(row, 0,  QtWidgets.QTableWidgetItem(link.href))
            self.links_table.setItem(row, 1, QtWidgets.QTableWidgetItem(link.rel))
            self.links_table.item(row, 2, QtWidgets.QTableWidgetItem(link.type))
            self.links_table.item(row, 3, QtWidgets.QTableWidgetItem(link.title))

    def set_providers(self, providers):

        self.providers_table.setRowCount(0)
        for provider in providers:
            self.providers_table.insertRow(self.providers_table.rowCount())
            row = self.providers_table.rowCount() - 1
            self.providers_table.item(row, 0, QtWidgets.QTableWidgetItem(provider.name))
            self.providers_table.item(row, 1, QtWidgets.QTableWidgetItem(provider.description))
            self.providers_table.item(row, 2, QtWidgets.QTableWidgetItem(provider.roles))
            self.providers_table.item(row, 3, QtWidgets.QTableWidgetItem(provider.url))
