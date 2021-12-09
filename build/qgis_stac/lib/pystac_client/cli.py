import argparse
import json
import logging
import os
import sys

from .client import Client
from .version import __version__

logger = logging.getLogger(__name__)


def search(client, method='GET', matched=False, save=None, **kwargs):
    """ Main function for performing a search """

    try:
        search = client.search(method=method, **kwargs)

        if matched:
            matched = search.matched()
            print('%s items matched' % matched)
        else:
            feature_collection = search.get_all_items_as_dict()
            if save:
                with open(save, 'w') as f:
                    f.write(json.dumps(feature_collection))
            else:
                print(json.dumps(feature_collection))

    except Exception as e:
        print(e)
        return 1


def collections(client, save=None, **kwargs):
    """ Fetch collections from collections endpoint """
    try:
        collections = client.get_all_collections(**kwargs)
        collections_dicts = [c.to_dict() for c in collections]
        if save:
            with open(save, 'w') as f:
                f.write(json.dumps(collections_dicts))
        else:
            print(json.dumps(collections_dicts))
    except Exception as e:
        print(e)
        return 1


def parse_args(args):
    desc = 'STAC Client'
    dhf = argparse.ArgumentDefaultsHelpFormatter
    parser0 = argparse.ArgumentParser(description=desc)
    parser0.add_argument('--version',
                         help='Print version and exit',
                         action='version',
                         version=__version__)

    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument('url', help='Root Catalog URL')
    parent.add_argument('--logging', default='INFO', help='DEBUG, INFO, WARN, ERROR, CRITICAL')
    parent.add_argument('--headers',
                        nargs='*',
                        help='Additional request headers (KEY=VALUE pairs)',
                        default=None)
    parent.add_argument('--ignore-conformance',
                        dest='ignore_conformance',
                        default=False,
                        action='store_true')

    subparsers = parser0.add_subparsers(dest='command')

    # collections command
    parser = subparsers.add_parser('collections',
                                   help='Get all collections in this Catalog',
                                   parents=[parent],
                                   formatter_class=dhf)
    output_group = parser.add_argument_group('output options')
    output_group.add_argument('--save', help='Filename to save collections to', default=None)

    # search command
    parser = subparsers.add_parser('search',
                                   help='Perform new search of items',
                                   parents=[parent],
                                   formatter_class=dhf)

    search_group = parser.add_argument_group('search options')
    search_group.add_argument('-c', '--collections', help='One or more collection IDs', nargs='*')
    search_group.add_argument('--ids',
                              help='One or more Item IDs (ignores other parameters)',
                              nargs='*')
    search_group.add_argument('--bbox',
                              help='Bounding box (min lon, min lat, max lon, max lat)',
                              nargs=4)
    search_group.add_argument('--intersects', help='GeoJSON Feature or geometry (file or string)')
    search_group.add_argument('--datetime',
                              help='Single date/time or begin and end date/time '
                              '(e.g., 2017-01-01/2017-02-15)')
    search_group.add_argument('-q',
                              '--query',
                              nargs='*',
                              help='Query properties of form '
                              'KEY=VALUE (<, >, <=, >=, = supported)')
    search_group.add_argument('--filter', help='Filter on queryables using CQL JSON')
    search_group.add_argument('--sortby', help='Sort by fields', nargs='*')
    search_group.add_argument('--fields', help='Control what fields get returned', nargs='*')
    search_group.add_argument('--limit', help='Page size limit', type=int, default=100)
    search_group.add_argument('--max-items',
                              dest='max_items',
                              help='Max items to retrieve from search',
                              type=int)
    search_group.add_argument('--method', help='GET or POST', default='POST')

    output_group = parser.add_argument_group('output options')
    output_group.add_argument('--matched',
                              help='Print number matched',
                              default=False,
                              action='store_true')
    output_group.add_argument('--save', help='Filename to save Item collection to', default=None)

    parsed_args = {k: v for k, v in vars(parser0.parse_args(args)).items() if v is not None}
    if "command" not in parsed_args:
        parser0.print_usage()
        return []

    # if intersects is JSON file, read it in
    if 'intersects' in parsed_args:
        if os.path.exists(parsed_args['intersects']):
            with open(parsed_args['intersects']) as f:
                data = json.loads(f.read())
                if data['type'] == 'Feature':
                    parsed_args['intersects'] = data['geometry']
                elif data['type'] == 'FeatureCollection':
                    parsed_args['intersects'] = data['features'][0]['geometry']
                else:
                    parsed_args['intersects'] = data

    # if headers provided, parse it
    if 'headers' in parsed_args:
        new_headers = {}
        for head in parsed_args['headers']:
            parts = head.split('=')
            if len(parts) == 2:
                new_headers[parts[0]] = parts[1]
            else:
                logger.warning(f"Unable to parse header {head}")
        parsed_args['headers'] = new_headers

    if 'filter' in parsed_args:
        parsed_args['filter'] = json.loads(parsed_args['filter'])

    return parsed_args


def cli():
    args = parse_args(sys.argv[1:])
    if not args:
        return None

    loglevel = args.pop('logging')
    if args.get('save', False) or args.get('matched', False):
        logging.basicConfig(level=loglevel)
        # quiet loggers
        logging.getLogger("urllib3").propagate = False

    cmd = args.pop('command')

    try:
        url = args.pop('url')
        headers = args.pop('headers', {})
        ignore_conformance = args.pop('ignore_conformance')
        client = Client.open(url, headers=headers, ignore_conformance=ignore_conformance)
    except Exception as e:
        print(e)
        return 1

    if cmd == 'search':
        return search(client, **args)
    elif cmd == 'collections':
        return collections(client, **args)


if __name__ == "__main__":
    return_code = cli()
    if return_code and return_code != 0:
        sys.exit(return_code)
