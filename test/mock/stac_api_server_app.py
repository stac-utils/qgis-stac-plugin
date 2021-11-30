import json

from pathlib import Path

from flask import Flask, request

app = Flask(__name__)

DATA_PATH = Path(__file__).parent / "data"


@app.route("/")
def catalog():
    catalog = DATA_PATH / "catalog.json"

    with catalog.open() as fl:
        return json.load(fl)


@app.route("/collections")
def collections():
    collections = DATA_PATH / "collections.json"

    with collections.open() as fl:
        return json.load(fl)


@app.route("/collections/<collection_id>")
def collection(collection_id):
    if collection_id == "simple-collection":
        collection = DATA_PATH / "collection.json"

        with collection.open() as fl:
            return json.load(fl)


@app.route("/collections/<collection_id>/items")
def items(collection_id):
    items_dict = {}
    if collection_id == "simple-collection":
        items_dict = {
            "type": "FeatureCollection",
            "features": []
        }
        files = [
            DATA_PATH / "first_item.json",
            DATA_PATH / "second_item.json"
        ]

        for f in files:
            with f.open() as fl:
                item = json.load(fl)
                items_dict["features"].append(item)
    return items_dict


@app.route("/search", methods=['GET', 'POST'])
def search():
    search_file = DATA_PATH / "search.json"

    with search_file.open() as fl:
        return json.load(fl)
