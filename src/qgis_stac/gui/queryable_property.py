# -*- coding: utf-8 -*-
"""
    Queryable property widget, used as a template for each property.
"""

import os

from qgis.gui import QgsDateTimeEdit

from qgis.PyQt import (
    QtCore,
    QtGui,
    QtNetwork,
    QtWidgets,
)
from qgis.PyQt.uic import loadUiType

from ..api.models import FilterOperator, QueryablePropertyType
from ..definitions.constants import STAC_QUERYABLE_TIMESTAMP


from ..utils import tr

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/queryable_property.ui")
)


class QueryablePropertyWidget(QtWidgets.QWidget, WidgetUi):
    """ Widget that provide UI for STAC queryable properties details.
    """

    def __init__(
        self,
        queryable_property,
        parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.queryable_property = queryable_property

        self.input_widget = None
        self.initialize_ui()

    def initialize_ui(self):
        """ Populate UI inputs when loading the widget"""

        size_policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred,
        )

        label = QtWidgets.QLabel(self.queryable_property.name)
        label.setSizePolicy(size_policy)

        label_layout = QtWidgets.QVBoxLayout(self.property_label)
        label_layout.setContentsMargins(9, 9, 9, 9)
        label_layout.addWidget(label)

        input_layout = QtWidgets.QVBoxLayout(self.property_input)
        input_layout.setContentsMargins(4, 4, 4, 4)

        if self.queryable_property.type == \
            QueryablePropertyType.INTEGER.value:
            spin_box = QtWidgets.QSpinBox()
            spin_box.setRange(
                self.queryable_property.minimum or 1,
                self.queryable_property.maximum or 100
            )
            spin_box.setSingleStep(1)
            spin_box.setSizePolicy(size_policy)

            input_layout.addWidget(spin_box)
            self.input_widget = spin_box
        elif self.queryable_property.type == \
            QueryablePropertyType.ENUM.value:

            cmb_box = QtWidgets.QComboBox()
            cmb_box.setSizePolicy(size_policy)

            cmb_box.addItem("")
            for enum_value in self.queryable_property.values:
                cmb_box.addItem(enum_value, enum_value)
            cmb_box.setCurrentIndex(0)

            input_layout.addWidget(cmb_box)
            self.input_widget = cmb_box
        elif self.queryable_property.type == \
            QueryablePropertyType.DATETIME.value:

            datetime_edit = QgsDateTimeEdit()
            datetime_edit.setSizePolicy(size_policy)

            input_layout.addWidget(datetime_edit)
            self.input_widget = datetime_edit
        else:
            line_edit = QtWidgets.QLineEdit()
            line_edit.setSizePolicy(size_policy)

            input_layout.addWidget(line_edit)
            self.input_widget = line_edit

        labels = {
            FilterOperator.LESS_THAN: tr("<"),
            FilterOperator.GREATER_THAN: tr(">"),
            FilterOperator.LESS_THAN_EQUAL: tr("<="),
            FilterOperator.GREATER_THAN_EQUAL: tr(">="),
            FilterOperator.EQUAL: tr("="),
        }
        self.operator_cmb.addItem("")
        for operator, label in labels.items():
            self.operator_cmb.addItem(label, operator)
        self.operator_cmb.setCurrentIndex(0)

    def filter_text(self):
        """ Returns a cql-text representation of the property and the
        available value.

        :returns CQL-Text that can be used to filter STAC catalog
        :rtype: str
        """

        try:
            current_operator = self.operator_cmb.itemData(
                self.operator_cmb.currentIndex()
            ) if self.operator_cmb.currentIndex() != 0 \
                else FilterOperator.EQUAL

            if isinstance(self.input_widget, QtWidgets.QSpinBox) and \
                    self.input_widget.value() != "":

                text = f"{self.queryable_property.name} " \
                       f"{current_operator.value} " \
                       f"{self.input_widget.value()}"
            elif isinstance(self.input_widget, QtWidgets.QLineEdit) and \
                    self.input_widget.text() != "":
                text = f"{self.queryable_property.name} " \
                       f"{current_operator.value} " \
                       f"{self.input_widget.text()}"
            elif isinstance(self.input_widget, QtWidgets.QComboBox):
                input_value = self.input_widget.itemData(
                    self.input_widget.currentIndex()
                )
                text = f"{self.queryable_property.name} " \
                       f"{current_operator.value} " \
                       f"{input_value}" if input_value else None
            elif isinstance(self.input_widget, QgsDateTimeEdit) and \
                    not self.input_widget.isNull():
                datetime_str = self.input_widget.dateTime().\
                    toString(QtCore.Qt.ISODate)
                text = f"{self.queryable_property.name} " \
                       f"{current_operator.value} " \
                       f"{STAC_QUERYABLE_TIMESTAMP}('{datetime_str}')"
            else:
                raise NotImplementedError
        except RuntimeError as e:
            text = None

        return text
