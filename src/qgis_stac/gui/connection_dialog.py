
import os
import uuid
import datetime

from qgis.PyQt import QtWidgets
from qgis.PyQt.uic import loadUiType
from ..conf import (
    ConnectionSettings,
    settings_manager
)

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

        if connection:
            self.load_connection_settings(connection)

    def load_connection_settings(self, connection_settings: ConnectionSettings):
        """ Sets this dialog inputs values as defined in the passed connection settings.

        :param connection_settings: Connection settings corresponding with the dialog.
        :type connection_settings: ConnectionSettings
        """
        self.name_edit.setText(connection_settings.name)
        self.url_edit.setText(connection_settings.url)
        self.auth_config.setConfigId(connection_settings.auth_config)
        self.page_size.setValue(connection_settings.page_size)

    def accept(self):
        """ Handles logic for adding new connections"""
        connection_id = uuid.uuid4()
        if self.connection is not None:
           connection_id = self.connection.id

        connection_settings = ConnectionSettings(
            id=connection_id,
            name=self.name_edit.text().strip(),
            url=self.url_edit.text().strip(),
            page_size=self.page_size.value(),
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
