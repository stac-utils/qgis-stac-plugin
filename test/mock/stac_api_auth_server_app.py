import json
import sys

from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)

DATA_PATH = Path(__file__).parent / "data"


@app.route("/")
def catalog():
    catalog = DATA_PATH / "catalog.json"

    with catalog.open() as fl:
        return json.load(fl)


@app.route("/collections")
def collections():
    headers = request.headers
    auth = headers.get("APIHeaderKey")
    if auth == 'test_api_header_key':
        collections = DATA_PATH / "collections.json"
        with collections.open() as fl:
            return json.load(fl)
    else:
        return jsonify({"message": "Unauthorized"}), 401
