import json
import sys

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


@app.route("/collections/<collection_id>/items", methods=['GET', 'POST'])
def items(collection_id):
    items_dict = {}
    if collection_id == "simple-collection":
        items_dict = {
            "type": "FeatureCollection",
            "features": []
        }
        sort_requested = False

        if request.method == 'POST':
            sort_params = request.json.get('sortby')
            sort_requested = sort_params is not None and (
                    sort_params[0].get('field') == 'id' and
                    sort_params[0].get('direction') == 'asc'
            )

        if sort_requested:
            files = [
                DATA_PATH / "first_item.json",
                DATA_PATH / "second_item.json",
                DATA_PATH / "third_item.json",
                DATA_PATH / "fourth_item.json",
            ]
        else:
            files = [
                DATA_PATH / "third_item.json",
                DATA_PATH / "fourth_item.json",
                DATA_PATH / "first_item.json",
                DATA_PATH / "second_item.json",
            ]

        for f in files:
            with f.open() as fl:
                item = json.load(fl)
                items_dict["features"].append(item)
    return items_dict


@app.route("/search", methods=['GET', 'POST'])
def search():
    sort_requested = False

    if request.method == 'POST':
        sort_params = request.json.get('sortby')
        sort_requested = sort_params is not None and (
                sort_params[0].get('field') == 'id' and
                sort_params[0].get('direction') == 'asc'
        )
    if sort_requested:
        search_file = DATA_PATH / "search_sorted.json"
    else:
        search_file = DATA_PATH / "search.json"

    with search_file.open() as fl:
        return json.load(fl)


@app.route("/conformance", methods=['GET'])
def conformance():
    conformance_file = DATA_PATH / "conformance.json"

    with conformance_file.open() as fl:
        return json.load(fl)
