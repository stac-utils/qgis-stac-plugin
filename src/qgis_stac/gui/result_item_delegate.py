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
from ..api.models import Item

from .result_item_widget import ResultItemWidget


class ResultItemDelegate(QtWidgets.QStyledItemDelegate):
    """ Result item class paints the item result widget into the
        provided view.
    """

    def __init__(
            self,
            main_widget,
            parent=None,
    ):
        super().__init__(parent)
        self.main_widget = main_widget
        self.parent = parent
        self.index = None

    def paint(
            self,
            painter,
            option,
            index,
    ):
        proxy_model = index.model()
        source_index = proxy_model.mapToSource(index)
        source_model = source_index.model()
        item = source_model.data(source_index, QtCore.Qt.DisplayRole)

        if isinstance(item, Item):
            item_widget = self.createEditor(self.parent, option, index)
            item_widget.setGeometry(option.rect)
            pixmap = item_widget.grab()
            painter.drawPixmap(option.rect.x(), option.rect.y(), pixmap)
        else:
            super().paint(painter, option, index)

    def sizeHint(
            self,
            option,
            index,
    ):
        proxy_model = index.model()
        source_index = proxy_model.mapToSource(index)
        source_model = source_index.model()
        item = source_model.data(source_index, QtCore.Qt.DisplayRole)

        if isinstance(item, Item):
            item_widget = self.createEditor(None, option, index)
            size = item_widget.size()
            del item_widget
            return size
        else:
            return super().sizeHint(option, index)

    def createEditor(
            self,
            parent,
            option,
            index,
    ):
        proxy_model = index.model()
        source_index = proxy_model.mapToSource(index)
        source_model = source_index.model()
        item = source_model.data(source_index, QtCore.Qt.DisplayRole)

        if isinstance(item, Item):
            return ResultItemWidget(
                item,
                main_widget=self.main_widget,
                parent=parent
            )
        else:
            return super().createEditor(parent, option, index)

    def updateEditorGeometry(
            self,
            editor,
            option,
            index,
    ):
        editor.setGeometry(option.rect)
