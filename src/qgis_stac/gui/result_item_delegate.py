# -*- coding: utf-8 -*-
"""
    Delegate logic used by the result tab tree view in loading the
    result item widget.
"""
from qgis.PyQt import (
    QtCore,
    QtGui,
    QtWidgets
)

from .result_item_widget import ResultItemWidget


class ResultItemDelegate(QtWidgets.QStyledItemDelegate):
    """ Result item class paints the item result widget into the
        provided view.
    """

    def __init__(
            self,
            parent=None,
    ):
        super().__init__(parent)
        self.parent = parent
        self.index = None

    def paint(
            self,
            painter: QtGui.QPainter,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex
    ):
        item_widget = self.createEditor(self.parent, option, index)
        item_widget.setGeometry(option.rect)
        pixmap = item_widget.grab()
        del item_widget
        painter.drawPixmap(option.rect.x(), option.rect.y(), pixmap)

    def sizeHint(
            self,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex
    ):
        item_widget = self.createEditor(None, option, index)
        size = item_widget.size()
        del item_widget
        return size

    def createEditor(
            self,
            parent: QtWidgets.QWidget,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex
    ):
        proxy_model = index.model()
        source_index = proxy_model.mapToSource(index)
        source_model = source_index.model()
        item = source_model.data(source_index, QtCore.Qt.DisplayRole)

        return ResultItemWidget(item, parent=parent)

    def updateEditorGeometry(
            self,
            editor: QtWidgets.QWidget,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex
    ):
        editor.setGeometry(option.rect)
