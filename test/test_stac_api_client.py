# coding=utf-8
"""Tests for the plugin STAC API client.

"""
import unittest

from multiprocessing import Process

from mock.mock_http_server import MockSTACApiServer
from qgis.PyQt.QtTest import QSignalSpy

from qgis_stac.api.client import Client
from qgis_stac.api.models import ItemSearch


class STACApiClientTest(unittest.TestCase):

    def setUp(self):

        app_server = MockSTACApiServer()

        self.server = Process(target=app_server.run)
        self.server.start()

        self.api_client = Client(app_server.url)
        self.response = None

    def test_resources_fetch(self):
        # check items searching
        spy = QSignalSpy(self.api_client.items_received)
        self.api_client.items_received.connect(self.app_response)
        self.api_client.get_items(ItemSearch(collections=['simple-collection']))
        result = spy.wait(timeout=1000)

        self.assertTrue(result)
        self.assertIsNotNone(self.response)
        self.assertEqual(len(self.response), 2)

        items = self.response[0]

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].id, "20201211_223832_CS1")
        self.assertEqual(items[1].id, "20201211_223832_CS2")

        # check conformance fetching
        spy = QSignalSpy(self.api_client.conformance_received)
        self.api_client.conformance_received.connect(self.app_response)
        self.api_client.get_conformance()
        result = spy.wait(timeout=1000)

        self.assertTrue(result)
        self.assertIsNotNone(self.response)
        self.assertEqual(len(self.response), 2)

        conformance_classes = self.response[0]

        self.assertEqual(len(conformance_classes), 16)
        self.assertEqual(conformance_classes[0].name, 'core')
        self.assertEqual(
            conformance_classes[0].uri,
            "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/core"
        )

    # TODO resolve self href error when iterating over collections
    # def test_collections_search(self):
    #
    #     api_client = Client(self.server.url)
    #     spy = QSignalSpy(api_client.collections_received)
    #     api_client.collections_received.connect(self.app_response)
    #     api_client.get_collections()
    #     result = spy.wait(timeout=1000)
    #
    #     self.assertTrue(result)
    #     self.assertIsNotNone(self.response)
    #     self.assertEqual(len(self.response), 2)
    #     collections = self.response[0]
    #
    #     self.assertEqual(len(collections), 1)
    #     self.assertEqual(collections[0].id, "simple-collection")
    #     self.assertEqual(collections[0].title, "Simple Example Collection")

    def app_response(self, *response_args):
        self.response = response_args

    def tearDown(self):
        self.server.terminate()
        self.server.join()


if __name__ == '__main__':
    unittest.main()

