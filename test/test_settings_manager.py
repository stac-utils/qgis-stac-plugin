# coding=utf-8
"""Tests for the plugin settings manager.

"""

import unittest

import uuid


from qgis_stac.conf import settings_manager
from qgis_stac.conf import ConnectionSettings


class SettingsManagerTest(unittest.TestCase):
    """Test the plugins setting manager"""

    def test_read_write_settings(self):
        """Settings manager can store and retrieve settings"""

        self.assertEqual(
            settings_manager.get_value(
                "non_existing_key",
                "none"
            ),
            "none"
        )
        self.assertIsNone(
            settings_manager.get_value(
                "non_existing_key")
        )
        settings_manager.set_value("name", "test")
        self.assertEqual(
            settings_manager.get_value(
                "name"
            ),
            "test"
        )
        settings_manager.remove("name")
        self.assertIsNone(
            settings_manager.get_value(
                "name")
        )

    def test_connection_settings(self):
        """Connection settings can be added, edited and removed"""

        self.assertEqual(
            settings_manager.get_value(
                "connections",
                "none"),
            "none"
        )

        # Check adding connection settings
        connection_id = uuid.uuid4()
        connection_name = f"connections/{str(connection_id)}/name"

        connection = ConnectionSettings(
            id=connection_id,
            name="test_connection",
            url="http:://test",
            page_size=10,
            collections=[],
            conformances=[],
            capability=None,
            sas_subscription_key=None,
            search_items=None,
        )

        self.assertIsNone(
            settings_manager.get_value(
                connection_name
            )
        )

        settings_manager.save_connection_settings(connection)

        self.assertIsNotNone(
            settings_manager.get_value(
                connection_name)
        )

        stored_connection = \
            settings_manager.get_connection_settings(
                connection_id
            )
        self.assertEqual(
            connection.auth_config,
            stored_connection.auth_config
        )

        self.assertEqual(
            connection.created_date.replace(second=0, microsecond=0),
            stored_connection.created_date.replace(second=0, microsecond=0)
        )

        # Adding a second connection, setting it a current selected
        # connection and checking if changes are in effect.
        second_connection_id = uuid.uuid4()
        second_connection = ConnectionSettings(
            id=second_connection_id,
            name="second_test_connection",
            url="http:://second_test",
            page_size=10,
            collections=[],
            conformances=[],
            capability=None,
            sas_subscription_key=None,
            search_items=None,
        )
        settings_manager.save_connection_settings(
            second_connection
        )
        second_stored_connection = \
            settings_manager.get_connection_settings(
                second_connection_id
            )
        self.assertEqual(
            second_connection.auth_config,
            second_stored_connection.auth_config
        )

        self.assertEqual(
            second_connection.created_date.replace(second=0, microsecond=0),
            second_stored_connection.created_date.replace(second=0, microsecond=0)
        )
        settings_manager.set_current_connection(
            second_connection_id
        )
        current_connection = settings_manager.get_current_connection()

        self.assertTrue(settings_manager.is_current_connection(
            second_connection_id
        ))

        self.assertEqual(
            second_connection.auth_config,
            current_connection.auth_config
        )

        self.assertEqual(
            second_connection.created_date.replace(second=0, microsecond=0),
            current_connection.created_date.replace(second=0, microsecond=0)
        )

        # Retrieve all the connections

        connections = settings_manager.list_connections()
        self.assertEqual(len(connections), 2)

        # Clear current connection
        settings_manager.clear_current_connection()
        current_connection = settings_manager.get_current_connection()
        self.assertIsNone(current_connection)

        # Remove connections
        settings_manager.delete_connection(second_connection_id)
        connections = settings_manager.list_connections()
        self.assertEqual(len(connections), 1)
