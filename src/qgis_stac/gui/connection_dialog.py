import os
import uuid
import datetime
import re

from qgis.PyQt import QtCore, QtGui, QtWidgets

from qgis.core import Qgis
from qgis.gui import QgsMessageBar

from qgis.PyQt.uic import loadUiType

from ..lib.pystac_client.conformance import ConformanceClasses
from ..lib.pystac_client.client import Client as STACClient
from ..conf import (
    ConnectionSettings,
    settings_manager
)

from ..api.models import ApiCapability, ResourceType
from ..api.client import Client
from ..utils import tr

DialogUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/connection_dialog.ui")
)


class ConnectionDialog(QtWidgets.QDialog, DialogUi):
    """ Dialog for adding and editing plugin connections details"""

    def __init__(
            self,
            connection=None
    ):
        """ Constructor

        :param connection: Connection settings
        :type connection: ConnectionSettings
        """
        super().__init__()
        self.setupUi(self)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.connection = connection

        ok_signals = [
            self.name_edit.textChanged,
            self.url_edit.textChanged,
        ]
        for signal in ok_signals:
            signal.connect(self.update_ok_buttons)

        if self.capabilities.count() == 0:
            self.capabilities.addItem(tr(""))
            for capability in ApiCapability:
                self.capabilities.addItem(capability.value)

        if connection:
            self.load_connection_settings(connection)

        self.grid_layout = QtWidgets.QGridLayout()
        self.message_bar = QgsMessageBar()

        self.prepare_message_bar()

        # prepare model for the conformance tree view
        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(
            [
                tr("Conformance type"),
                tr("Conformance URI")
            ]
        )
        self.proxy_model = QtCore.QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setDynamicSortFilter(True)
        self.proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.conformances_tree.setModel(self.proxy_model)
        self.get_conformances_btn.clicked.connect(self.search_conformances)

    def search_conformances(self):
        """ Searches for the conformances available on the current
            STAC API connection.
        """

        connection = self.get_connection()
        conformances = []
        self.model.removeRows(0, self.model.rowCount())
        if connection is not None:
            api_client = Client.from_connection_settings(connection)
            client = STACClient.open(api_client.url)
            if client._stac_io._conformance is None:
                self.show_message(
                    tr("No conformance class was found"),
                    Qgis.Info
                )
                return
            for uri in client._stac_io._conformance:
                for conformance in ConformanceClasses:
                    if conformance == ConformanceClasses.stac_prefix:
                        continue
                    pattern = re.compile(conformance.value)
                    if re.match(pattern, uri):
                        conformances.append(conformance)
                        item_name = QtGui.QStandardItem(
                            conformance.name
                        )
                        item_value = QtGui.QStandardItem(
                            uri
                        )
                        self.model.appendRow([item_name, item_value])

            self.proxy_model.setSourceModel(self.model)
            self.proxy_model.sort(QtCore.Qt.DisplayRole)
            self.show_message(
                tr("{} conformance class(es) was found").format(len(conformances)),
                Qgis.Info
            )

    def prepare_message_bar(self):
        """ Initializes the widget message bar settings"""
        self.message_bar.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Fixed
        )
        self.grid_layout.addWidget(
            self.connection_box,
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

    def get_connection(self):
        connection_id = uuid.uuid4()
        if self.connection is not None:
            return self.connection

        capability = None
        if self.capabilities.currentText() != "":
            capability = ApiCapability(self.capabilities.currentText())

        connection_settings = ConnectionSettings(
            id=connection_id,
            name=self.name_edit.text().strip(),
            url=self.url_edit.text().strip(),
            page_size=self.page_size.value(),
            collections=[],
            capability=capability,
            created_date=datetime.datetime.now(),
            auth_config=self.auth_config.configId(),
        )

        return connection_settings

    def load_connection_settings(self, connection_settings: ConnectionSettings):
        """ Sets this dialog inputs values as defined in the passed connection settings.

        :param connection_settings: Connection settings corresponding with the dialog.
        :type connection_settings: ConnectionSettings
        """
        self.name_edit.setText(connection_settings.name)
        self.url_edit.setText(connection_settings.url)
        self.auth_config.setConfigId(connection_settings.auth_config)
        self.page_size.setValue(connection_settings.page_size)
        capability_index = self.capabilities.findText(
            connection_settings.capability.value
        ) if connection_settings.capability else 0
        self.capabilities.setCurrentIndex(capability_index)

    def accept(self):
        """ Handles logic for adding new connections"""
        connection_id = uuid.uuid4()
        if self.connection is not None:
            connection_id = self.connection.id

        capability = None
        if self.capabilities.currentText() != "":
            capability = ApiCapability(self.capabilities.currentText())

        connection_settings = ConnectionSettings(
            id=connection_id,
            name=self.name_edit.text().strip(),
            url=self.url_edit.text().strip(),
            page_size=self.page_size.value(),
            collections=[],
            capability=capability,
            created_date=datetime.datetime.now(),
            auth_config=self.auth_config.configId(),
        )
        existing_connection_names = []
        if connection_settings.name in (
                connection.name for connection in
                settings_manager.list_connections()
                if connection.id != connection_settings.id
        ):
            existing_connection_names.append(connection_settings.name)
        if len(existing_connection_names) > 0:
            connection_settings.name = f"{connection_settings.name}" \
                                       f"({len(existing_connection_names)})"
        settings_manager.save_connection_settings(connection_settings)
        settings_manager.set_current_connection(connection_settings.id)
        super().accept()

    def update_ok_buttons(self):
        """ Responsible for changing the state of the
         connection dialog OK button.
        """
        enabled_state = self.name_edit.text() != "" and \
                        self.url_edit.text() != ""
        self.buttonBox.button(
            QtWidgets.QDialogButtonBox.Ok).setEnabled(enabled_state)
        self.get_conformances_btn.setEnabled(enabled_state)
