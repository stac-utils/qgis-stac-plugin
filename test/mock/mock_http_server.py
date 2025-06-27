import requests
import socket

from flask import request
from threading import Thread
from time import sleep, time
from typing import Final

from .stac_api_server_app import app
from .stac_api_auth_server_app import app as auth_app


_host: Final[str] = "localhost"
_default_port: Final[int] = 5000

class MockSTACApiServer(Thread):
    """ Mock a live """
    def __init__(self, port=_default_port, auth=False):
        super().__init__()
        self.port = port

        if not auth:
            self.app = app
        else:
            self.app = auth_app

        self.url = "http://%s:%s" % (_host, self.port)

        try:
            self.app.add_url_rule("/shutdown", view_func=self._shutdown_server)
        except AssertionError as ae:
            pass

    def _shutdown_server(self):
        if not 'werkzeug.server.shutdown' in request.environ:
            raise RuntimeError('Error shutting down server')
        request.environ['werkzeug.server.shutdown']()
        return 'Shutting down'

    def shutdown_server(self):
        requests.get("http://localhost:%s/shutdown" % self.port)
        self.join()

    def run(self):
        self.app.run(port=self.port)

    def wait_for_ready(self, wait_timeout_seconds: int = 5) -> None:
        start = time()
        while time() - start < wait_timeout_seconds:
            try:
                socket.create_connection((_host, self.port), timeout=1)
                return
            except (ConnectionRefusedError, OSError):
                sleep(1)
        raise Exception("Unable to establish a connection to server at %s:%s in %ss" % (_host, self.port, wait_timeout_seconds))
