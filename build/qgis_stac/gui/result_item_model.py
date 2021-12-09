# -*- coding: utf-8 -*-
"""
    Contains GUI models used to store search result items.
"""
from qgis.PyQt import (
    QtCore,
    QtGui,
    QtWidgets
)

from ..api.models import SortField


class ItemsModel(QtCore.QAbstractItemModel):
    """ Stores the search result items"""

    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items

    def index(
            self,
            row: int,
            column: int,
            parent
    ):
        invalid_index = QtCore.QModelIndex()
        if self.hasIndex(row, column, parent):
            try:
                item = self.items[row]
                result = self.createIndex(row, column, item)
            except IndexError:
                result = invalid_index
        else:
            result = invalid_index
        return result

    def parent(self, index: QtCore.QModelIndex):
        return QtCore.QModelIndex()

    def rowCount(self, index: QtCore.QModelIndex = QtCore.QModelIndex()):
        return len(self.items)

    def columnCount(self, index: QtCore.QModelIndex = QtCore.QModelIndex()):
        return 1

    def data(
            self,
            index: QtCore.QModelIndex = QtCore.QModelIndex(),
            role: QtCore.Qt.ItemDataRole = QtCore.Qt.DisplayRole
    ):
        result = None
        if index.isValid():
            item = index.internalPointer()
            result = item
        return result

    def flags(
            self,
            index: QtCore.QModelIndex = QtCore.QModelIndex()
    ):
        if index.isValid():
            flags = super().flags(index)
            result = QtCore.Qt.ItemIsEditable | flags
        else:
            result = QtCore.Qt.NoItemFlags
        return result


class ItemsSortFilterProxyModel(QtCore.QSortFilterProxyModel):
    """ Handles the custom functionality in sorting and filtering the
    search items results.
    """

    def __init__(self, current_sort_field, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_sort_field = current_sort_field

    def lessThan(self, left: QtCore.QModelIndex, right: QtCore.QModelIndex) -> bool:
        model = self.sourceModel()
        left_item = model.data(left)
        right_item = model.data(right)

        if self.current_sort_field == SortField.DATE:
            result = left_item.id < right_item.id
        else:
            raise NotImplementedError

        return result
