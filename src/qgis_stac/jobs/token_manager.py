# -*- coding: utf-8 -*-
"""
    Handles the plugin connection Token management.
"""

from qgis.PyQt import (
    QtCore,
)

from ..conf import settings_manager
from ..lib import planetary_computer as pc

from ..api.models import (
    ApiCapability,
)


class SASManager(QtCore.QObject):
    """ Manager to help updates on the SAS token based connections.
    """
    token_refresh_started = QtCore.pyqtSignal()
    token_refresh_finished = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def token_refresh(self):
        """ Refreshes the current SAS token available in search results
         items store in the plugin settings.
         """
        updated_items = []

        self.token_refresh_started.emit()

        connections = settings_manager.list_connections()

        for connection in connections:
            if connection.capability == \
                    ApiCapability.SUPPORT_SAS_TOKEN:
                settings_items = settings_manager.get_items(
                    connection.id
                )
                for page, items in settings_items.items():
                    for item in items:
                        if item.stac_object:
                            stac_object = pc.sign(item.stac_object)
                            item.stac_object = stac_object
                            updated_items.append(item)
                    if updated_items:
                        settings_manager.save_items(
                            connection,
                            updated_items,
                            page
                        )
                        updated_items = []

        self.token_refresh_finished.emit()
