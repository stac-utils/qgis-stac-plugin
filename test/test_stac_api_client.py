# coding=utf-8
"""Tests for the plugin STAC API client.

"""
import unittest

from mock.stac_api_server import app


class STACApiClientTest(unittest.TestCase):

    def test_root(self):
        response = app.test_client().get('/api/v1')
        self.assertEqual(response.status_code, 201)


if __name__ == '__main__':
    unittest.main()
