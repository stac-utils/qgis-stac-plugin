import os

from qgis.PyQt import QtWidgets
from qgis.PyQt.uic import loadUiType

from ..resources import *


WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/result_item_widget.ui")
)


class ResultItemWidget(QtWidgets.QWidget, WidgetUi):

    def __init__(
        self,
        item,
        parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.item = item
        self.title_la.setText(item.id)
