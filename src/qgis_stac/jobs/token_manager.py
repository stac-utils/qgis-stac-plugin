# -*- coding: utf-8 -*-
"""
    Handles the plugin connection Token management.
"""

import os
import enum

from qgis.PyQt import (
    QtCore,
)

from qgis.core import (
    QgsApplication,
    QgsTask
)

from ..conf import Settings, settings_manager
from ..lib import planetary_computer as pc

from ..api.models import (
    ApiCapability,
    ResourceAsset,
    TimeUnits
)

from ..utils import log

from ..definitions.constants import SAS_SUBSCRIPTION_VARIABLE


class RefreshState(enum.Enum):
    """ Represents time units."""
    RUNNING = 'RUNNING'
    IDLE = 'IDLE'


class SASManager(QtCore.QObject):
    """ Manager to help updates on the SAS token based connections.
    """
    token_refresh_started = QtCore.pyqtSignal()
    token_refresh_finished = QtCore.pyqtSignal()
    token_refresh_error = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def refresh_started(self):
        self.token_refresh_started.emit()

    def refresh_complete(self):

        settings_manager.set_value(
            Settings.REFRESH_STATE,
            RefreshState.IDLE
        )
        self.token_refresh_finished.emit()

    def refresh_error(self):

        settings_manager.set_value(
            Settings.REFRESH_STATE,
            RefreshState.IDLE
        )
        self.token_refresh_error.emit()

    def run_refresh_task(self):

        refresh_state = settings_manager.get_value(
            Settings.REFRESH_STATE,
            RefreshState.IDLE
        )

        if refresh_state == RefreshState.RUNNING:
            return

        self.token_refresh_started.emit()

        task = RefreshTask()
        task.taskCompleted.connect(self.refresh_complete)
        task.taskTerminated.connect(self.refresh_error)
        task.run()


class RefreshTask(QgsTask):
    """ Runs token manager refresh process on a background Task."""
    def __init__(
        self
    ):

        super().__init__()

    def run(self):
        """ Operates the main logic of loading the token refreshin
        background.
        """
        self.token_refresh()

        return True

    def token_refresh(self):
        """ Refreshes the current SAS token available in search results
         items store in the plugin settings.
         """
        updated_items = []

        last_update = settings_manager.get_value(
            Settings.REFRESH_LAST_UPDATE,
            None
        )

        refresh_frequency = settings_manager.get_value(
            Settings.REFRESH_FREQUENCY,
            1,
            setting_type=int
        )

        unit = settings_manager.get_value(
            Settings.REFRESH_FREQUENCY_UNIT,
            TimeUnits.MINUTES
        )

        refresh_time_count = {
            TimeUnits.MINUTES: 60000,
            TimeUnits.HOURS: 60 * 6000,
            TimeUnits.DAYS: 24 * 60 * 6000,
        }

        if last_update:
            last_update_date = QtCore.QDateTime.fromString(
                    last_update, QtCore.Qt.ISODate
            )
        else:
            last_update_date = QtCore.QDateTime.currentDateTime()
            settings_manager.set_value(
                Settings.REFRESH_LAST_UPDATE,
                last_update_date.toString(QtCore.Qt.ISODate)
            )

        current_time = QtCore.QDateTime.currentDateTime()

        if last_update_date.msecsTo(current_time) < \
            refresh_frequency * refresh_time_count[unit]:
            self.cancel()
            return

        settings_manager.set_value(
            Settings.REFRESH_LAST_UPDATE,
            current_time.toString(QtCore.Qt.ISODate)
        )

        settings_manager.set_value(
            Settings.REFRESH_STATE,
            RefreshState.RUNNING
        )

        connections = settings_manager.list_connections()

        key = os.getenv(SAS_SUBSCRIPTION_VARIABLE)

        # If the plugin defined connection sas subscription key
        # exists use it instead of the environment one.
        connection = settings_manager.get_current_connection()

        if connection and \
                connection.capability == ApiCapability.SUPPORT_SAS_TOKEN and \
                connection.sas_subscription_key:
            key = connection.sas_subscription_key

        if key:
            pc.set_subscription_key(key)

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
                            item.assets = [
                                ResourceAsset(
                                    href=asset.href,
                                    title=asset.title or key,
                                    description=asset.description,
                                    type=asset.media_type,
                                    roles=asset.roles or []
                                )
                                for key, asset in stac_object.assets.items()
                            ]
                            updated_items.append(item)
                    if updated_items:
                        settings_manager.save_items(
                            connection,
                            updated_items,
                            page
                        )
                        updated_items = []

        self.cancel()


    def finished(self, result: bool):
        """ Handle logic after task has completed.

        :param result: Whether the run() operation finished successfully
        :type result: bool
        """
        if result:
            log("Successfully refreshed")
            settings_manager.set_value(
                Settings.REFRESH_STATE,
                RefreshState.IDLE
            )
        else:
            log("Failed to refresh")

