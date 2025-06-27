# coding=utf-8
"""Tests for the plugin STAC API client.

"""
import unittest
import logging

from multiprocessing import Process

from mock.mock_http_server import MockSTACApiServer
from qgis.PyQt.QtTest import QSignalSpy

from qgis_stac.api.client import Client
from qgis.core import QgsApplication
from qgis.core import QgsAuthMethodConfig


class STACApiClientAuthTest(unittest.TestCase):

    def setUp(self):
        self.app_server = MockSTACApiServer(auth=True)

        self.server = Process(target=self.app_server.run)
        self.server.start()
        self.app_server.wait_for_ready()

        self.api_client = Client(self.app_server.url)
        self.response = None
        self.error = None

    def set_auth_method(
            self,
            config_name,
            config_method,
            config_map
    ):
        AUTHDB_MASTERPWD = "password"

        auth_manager = QgsApplication.authManager()
        if not auth_manager.masterPasswordHashInDatabase():
            auth_manager.setMasterPassword(AUTHDB_MASTERPWD, True)
            # Create config
            auth_manager.authenticationDatabasePath()
            auth_manager.masterPasswordIsSet()

        cfg = QgsAuthMethodConfig()
        cfg.setName(config_name)
        cfg.setMethod(config_method)
        cfg.setConfigMap(config_map)
        auth_manager.storeAuthenticationConfig(cfg)

        return cfg.id()

    def test_auth_collections_fetch(self):
        # check if auth works correctly
        cfg_id = self.set_auth_method(
            "STAC_API_AUTH_TEST",
            "APIHeader",
            {"APIHeaderKey": "test_api_header_key"}
        )

        api_client = Client(
            self.app_server.url,
            auth_config=cfg_id
        )

        spy = QSignalSpy(api_client.collections_received)
        api_client.collections_received.connect(self.app_response)
        api_client.error_received.connect(self.error_response)

        api_client.get_collections()
        result = spy.wait(timeout=1000)

        self.assertTrue(result)
        self.assertIsNotNone(self.response)
        self.assertIsNone(self.error)
        self.assertEqual(len(self.response), 2)

        cfg_id = self.set_auth_method(
            "STAC_API_AUTH_TEST",
            "APIHeader",
            {"APIHeaderKey": "unauthorized_api_header_key"}
        )

        api_client = Client(
            self.app_server.url,
            auth_config=cfg_id
        )

        spy = QSignalSpy(api_client.collections_received)
        api_client.collections_received.connect(self.app_response)
        api_client.error_received.connect(self.error_response)

        api_client.get_collections()
        result = spy.wait(timeout=1000)

        self.assertFalse(result)
        self.assertIsNotNone(self.error)

    def app_response(self, *response_args):
        self.response = response_args

    def error_response(self, *response_args):
        self.error = response_args

    def tearDown(self):
        self.server.terminate()
        self.server.join()


if __name__ == '__main__':
    unittest.main()
