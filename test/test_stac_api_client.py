# coding=utf-8
"""Tests for the plugin STAC API client.

"""
import unittest
import re

from multiprocessing import Process

from mock.mock_http_server import MockSTACApiServer
from qgis.PyQt.QtTest import QSignalSpy

from qgis_stac.api.client import Client
from qgis_stac.api.models import ItemSearch, SortField, SortOrder

from qgis_stac.lib.pystac_client.conformance import ConformanceClasses, CONFORMANCE_URIS
from qgis_stac.lib.pystac_client import Client as STACClient


class STACApiClientTest(unittest.TestCase):

    def setUp(self):

        self.app_server = MockSTACApiServer()

        self.server = Process(target=self.app_server.run)
        self.server.start()

        self.api_client = Client(self.app_server.url)
        self.response = None
        self.error = None

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

        self.assertEqual(len(items), 4)
        self.assertEqual(items[0].id, "20201211_223832_CS3")
        self.assertEqual(items[1].id, "20201211_223832_CS4")

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

    def test_items_sort(self):
        # check items searching with sorting enabled
        spy = QSignalSpy(self.api_client.items_received)
        self.api_client.items_received.connect(self.app_response)

        self.api_client.get_items(
            ItemSearch(
                collections=['simple-collection'],
                sortby=SortField.ID,
                sort_order=SortOrder.ASCENDING
            )
        )
        result = spy.wait(timeout=1000)

        self.assertTrue(result)
        self.assertIsNotNone(self.response)
        self.assertEqual(len(self.response), 2)
        items = self.response[0]

        self.assertEqual(len(items), 4)
        self.assertEqual(items[0].id, "20201211_223832_CS1")
        self.assertEqual(items[1].id, "20201211_223832_CS2")

    def test_collections_search(self):

        api_client = Client(self.app_server.url)
        spy = QSignalSpy(api_client.collections_received)
        api_client.collections_received.connect(self.app_response)
        api_client.get_collections()
        result = spy.wait(timeout=1000)

        self.assertTrue(result)
        self.assertIsNotNone(self.response)
        self.assertEqual(len(self.response), 2)
        collections = self.response[0]

        self.assertEqual(len(collections), 1)
        self.assertEqual(collections[0].id, "simple-collection")
        self.assertEqual(collections[0].title, "Simple Example Collection")

    def test_conformance_search(self):

        api_client = Client(self.app_server.url)
        spy = QSignalSpy(api_client.conformance_received)
        api_client.conformance_received.connect(self.app_response)
        api_client.get_conformance()
        result = spy.wait(timeout=1000)

        self.assertTrue(result)
        self.assertIsNotNone(self.response)
        self.assertEqual(len(self.response), 2)
        conformances = self.response[0]

        self.assertEqual(len(conformances), 16)

    def conforms_to(self, conformance_class: ConformanceClasses) -> bool:
        stac_client = STACClient.open(self.app_server.url)

        if stac_client._stac_io._conformance is None:
            return True

        class_regex = CONFORMANCE_URIS.get(conformance_class.name, None)

        if class_regex is None:
            raise Exception(f"Invalid conformance class {conformance_class}")

        pattern = re.compile(class_regex)
        print("Pattern")
        print(pattern)

        if not any(re.match(pattern, uri) for uri in stac_client._stac_io._conformance):
            return False

        return True

    def app_response(self, *response_args):
        self.response = response_args

    def error_response(self, *response_args):
        self.error = response_args

    def tearDown(self):
        self.server.terminate()
        self.server.join()


if __name__ == '__main__':
    unittest.main()

