import os

from qgis.PyQt import QtCore, QtGui, QtWidgets


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
            self.title.setText(self.collection.title)
