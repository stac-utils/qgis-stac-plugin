# -*- coding: utf-8 -*-

"""
 Connection dialog class file
"""

import datetime
import os
import uuid

from functools import partial

from qgis.PyQt import QtCore, QtGui, QtWidgets

from qgis.core import Qgis
from qgis.gui import QgsMessageBar

from qgis.PyQt.uic import loadUiType

from ..conf import (
    ConnectionSettings,
    settings_manager
)

from ..api.models import ApiCapability, ItemSearch
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
        self.buttonBox.button(
            QtWidgets.QDialogButtonBox.Ok
        ).setEnabled(False)
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
        self.get_conformances_btn.clicked.connect(self.fetch_conformances)

        if connection:
            self.sas_subscription_key.setText(
                connection.sas_subscription_key
            ) if connection.sas_subscription_key else None

            self.load_connection_settings(connection)
            self.conformance = connection.conformances
            self.setWindowTitle(tr("Edit Connection"))
        else:
            self.conformance = []

        self.sas_subscription_key_la.setEnabled(
            connection is not None and
            connection.capability == ApiCapability.SUPPORT_SAS_TOKEN
        )
        self.sas_subscription_key.setEnabled(
            connection is not None and
            connection.capability == ApiCapability.SUPPORT_SAS_TOKEN
        )

        self.test_btn.clicked.connect(self.test_connection)

        self.grid_layout = QtWidgets.QGridLayout()
        self.message_bar = QgsMessageBar()
        self.progress_bar = QtWidgets.QProgressBar()

        self.prepare_message_bar()

    def fetch_conformances(self):
        """ Fetches the conformances available on the current
            STAC API connection.
        """
        connection = self.get_connection()

        if connection is not None:
            self.update_connection_inputs(False)
            api_client = Client.from_connection_settings(connection)
            api_client.conformance_received.connect(self.display_conformances)
            api_client.error_received.connect(self.show_message)
            update_inputs = partial(self.update_connection_inputs, True)
            api_client.error_received.connect(update_inputs)
            self.show_progress(
                tr("Getting API conformance classes..."),
                progress_bar=False
            )
            api_client.get_conformance()

    def display_conformances(self, conformance_results, pagination):
        """ Displays the found conformance classes in the dialog conformance view

        :param conformance_results: List of the fetched conformance classes uris
        :type conformance_results: list

        :param pagination: Information about pagination
        :type pagination: ResourcePagination
        """
        # TODO make use of pagination or change function signature to not accept
        # pagination
        self.load_conformances(conformance_results)
        self.conformance = conformance_results
        connection = self.get_connection()
        settings_manager.delete_all_conformance(connection)

        self.show_message(
            tr("{} conformance class(es) was found").format(
                len(self.conformance)
            ),
            Qgis.Info
        )
        self.update_connection_inputs(True)

    def load_conformances(self, conformances):
        """ Loads the passed list of conformances into the Connection conformances
        view

        :param conformances: List of conformances settings
        :type conformances: list
        """
        self.model.removeRows(0, self.model.rowCount())
        for conformance in conformances:
            item_name = QtGui.QStandardItem(
                conformance.name.upper()
            )
            item_uri = QtGui.QStandardItem(
                conformance.uri
            )
            self.model.appendRow([item_name, item_uri])

        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.sort(QtCore.Qt.DisplayRole)

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

    def show_progress(
            self,
            message,
            minimum=0,
            maximum=0,
            progress_bar=True):
        """ Shows the progress message on the main widget message bar

        :param message: Progress message
        :type message: str

        :param minimum: Minimum value that can be set on the progress bar
        :type minimum: int

        :param maximum: Maximum value that can be set on the progress bar
        :type maximum: int

        :param progress_bar: Whether to show progress bar status
        :type progress_bar: bool
        """
        self.message_bar.clearWidgets()
        message_bar_item = self.message_bar.createMessage(message)
        try:
            self.progress_bar.isEnabled()
        except RuntimeError as er:
            self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        if progress_bar:
            self.progress_bar.setMinimum(minimum)
            self.progress_bar.setMaximum(maximum)
        else:
            self.progress_bar.setMaximum(0)
        message_bar_item.layout().addWidget(self.progress_bar)
        self.message_bar.pushWidget(message_bar_item, Qgis.Info)

    def get_connection(self):
        """ Get the connection instance using the current API
        details from this connection dialog.
        """
        if self.connection is not None:
            if self.connection.url != self.url_edit.text().strip():
                self.connection.url = self.url_edit.text().strip()
            return self.connection

        connection_id = uuid.uuid4()
        capability = None
        search_items = []

        sas_subscription_key = self.sas_subscription_key.text()

        if self.capabilities.currentText() != "":
            capability = ApiCapability(self.capabilities.currentText())

        connection_settings = ConnectionSettings(
            id=connection_id,
            name=self.name_edit.text().strip(),
            url=self.url_edit.text().strip(),
            page_size=self.page_size.value(),
            collections=[],
            capability=capability,
            conformances=self.conformance,
            created_date=datetime.datetime.now(),
            auth_config=self.auth_config.configId(),
            search_items=search_items,
            sas_subscription_key=sas_subscription_key,
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
        if connection_settings.conformances:
            self.load_conformances(connection_settings.conformances)

    def accept(self):
        """ Handles logic for adding new connections"""
        connection_id = uuid.uuid4()
        if self.connection is not None:
            connection_id = self.connection.id

        capability = None
        if self.capabilities.currentText() != "":
            capability = ApiCapability(self.capabilities.currentText())

        sas_subscription_key = None
        if self.sas_subscription_key.text() != "":
            sas_subscription_key = self.sas_subscription_key.text()

        connection_settings = ConnectionSettings(
            id=connection_id,
            name=self.name_edit.text().strip(),
            url=self.url_edit.text().strip(),
            page_size=self.page_size.value(),
            collections=[],
            capability=capability,
            sas_subscription_key=sas_subscription_key,
            conformances=self.conformance,
            created_date=datetime.datetime.now(),
            auth_config=self.auth_config.configId(),
            search_items=[]
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
        self.test_btn.setEnabled(enabled_state)

    def update_connection_inputs(self, enabled):
        """ Sets the connection inputs state using
        the provided enabled status

        :param enabled: Whether to enable the inputs
        :type enabled: bool
        """
        self.connection_box.setEnabled(enabled)

    def test_connection(self):
        """ Test the current set connection if it is a valid
        STAC API connection
        """
        connection = self.get_connection()
        if connection is not None:
            self.update_connection_inputs(False)
            api_client = Client.from_connection_settings(connection)
            connection_test_success = partial(
                self.connection_test,
                True
            )
            connection_test_fail = partial(
                self.connection_test,
                False
            )

            api_client.items_received.connect(connection_test_success)
            api_client.error_received.connect(connection_test_fail)
            self.show_progress(
                tr("Testing connection..."),
                progress_bar=False
            )
            api_client.get_items(
                ItemSearch(
                    page_size=1
                )
            )

    def connection_test(
            self,
            success,
            payload,
    ):
        """ Relays information to user about the connection test results
        and updates the UI to enable connection inputs.

        :param success: If the connection test was successful
        :type success: bool

        :param payload: The returned payload after the test operation
        :type payload: list
        """
        if success:
            self.show_message(
                tr("Connection is a valid STAC API"),
                level=Qgis.Info)
        else:
            self.show_message(
                tr("Connection is not a valid STAC API"),
                level=Qgis.Critical)
        self.update_connection_inputs(True)
