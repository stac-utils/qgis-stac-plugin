# -*- coding: utf-8 -*-
"""
    Queryable property widget, used as a template for each property.
"""

import os

from functools import partial

from qgis.PyQt import (
    QtGui,
    QtCore,
    QtWidgets,
    QtNetwork
)
from qgis.PyQt.uic import loadUiType

from ..api.models import QueryablePropertyType

from ..conf import Settings, settings_manager

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

        label = QtWidgets.QLabel(self.queryable_property.name)
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
            input_layout.addWidget(spin_box)
            self.input_widget = spin_box
        elif self.queryable_property.type == \
            QueryablePropertyType.ENUM.value:

            cmb_box = QtWidgets.QComboBox()
            self.cmb_cmb.addItem("")
            for enum_value in self.queryable_property.values:
                self.cmb_box.addItem(enum_value, enum_value)
            self.cmb_box.setCurrentIndex(0)

            input_layout.addWidget(cmb_box)
            self.input_widget = cmb_box
        else:
            line_edit = QtWidgets.QLineEdit()
            input_layout.addWidget(line_edit)
            self.input_widget = line_edit

    def filter_text(self):
        """ Returns a cql-text representation of the property and the
        available value."""

        if isinstance(self.input_widget, QtWidgets.QSpinBox):

            text = f"{self.queryable_property.name} = " \
                   f"{self.input_widget.value()}"
        elif isinstance(self.input_widget, QtWidgets.QLineEdit):
            text = f"{self.queryable_property.name} = " \
                   f"{self.input_widget.text()}"
        else:
            raise NotImplementedError

        return text


