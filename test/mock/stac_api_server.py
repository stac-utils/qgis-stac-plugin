import json

from pathlib import Path

from flask import Flask, request

app = Flask("mock_stac_api_server")

DATA_PATH = Path(__file__).parent / "data"


@app.route("/api/v1")
def catalog():
    catalog = DATA_PATH / "catalog.json"

    with catalog.open() as fl:
        return json.load(fl)


@app.route("/api/v1/collections")
def collections():
    collections = DATA_PATH / "collections.json"

    with collections.open() as fl:
        return json.load(fl)


@app.route("/api/v1/<collection_id>")
def collection(collection_id):
    if collection_id is "simple-collection":
        collection = "collection.json"

        with collection.open() as fl:
            return json.load(fl)


@app.route("/api/v1/<collection_id>/items")
def collection(collection_id):
    items = {}
    if collection_id is "simple-collection":
        items = {
            "type": "FeatureCollection",
            "features": []
        }
        files = ["first_item.json", "second_item.json"]

        for f in files:
            with f.open() as fl:
                item = json.load(fl)
                items["features"].append(item)
    return items
