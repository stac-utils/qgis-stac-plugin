import os
import re
import uuid
import typing
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

    def __init__(self,
                 connection_settings: typing.Optional[ConnectionSettings] = None
                 ):
        super().__init__()
        self.setupUi(self)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        ok_signals = [
            self.name_edit.textChanged,
            self.url_edit.textChanged,
        ]
        for signal in ok_signals:
            signal.connect(self.update_ok_buttons)

    def load_connection_settings(self, connection_settings: ConnectionSettings):
        self.name_edit.setText(connection_settings.name)
        self.url_edit.setText(connection_settings.base_url)
        self.auth_config.setConfigId(connection_settings.auth_config)
        self.page_size.setValue(connection_settings.page_size)

    def accept(self):
        connection_settings = ConnectionSettings(
            id=uuid.uuid4(),
            name=self.name_edit.text().strip(),
            url=self.url_edit.text().strip(),
            page_size=self.page_size.value(),
            auth_config=self.auth_config.configId(),
        )
        existing_connection_names = []
        if connection_settings.name in (connexion.name for connexion in settings_manager.list_connections()):
            existing_connection_names.append(connection_settings.name)
        if len(existing_connection_names) > 0:
            connection_settings.name = f"{connection_settings.name}_{len(existing_connection_names)}"
        settings_manager.save_connection_settings(connection_settings)
        settings_manager.set_current_connection(connection_settings.id)
        super().accept()

    def update_ok_buttons(self):
        enabled_state = self.name_edit.text() != "" and self.url_edit.text() != ""
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(enabled_state)
