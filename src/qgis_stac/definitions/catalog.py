# -*- coding: utf-8 -*-
"""
    Definitions for all pre-installed STAC API catalog connections
"""

from ..api.models import ApiCapability

CATALOGS = [
    {
        "id": "07e3e9dd-cbad-4cf6-8336-424b88abf8f3",
        "name": "Microsoft Planetary Computer STAC API",
        "url": "https://planetarycomputer.microsoft.com/api/stac/v1",
        "selected": True,
        "capability": ApiCapability.SUPPORT_SAS_TOKEN.value
    },
    {
        "id": "d74817bf-da1f-44d7-a464-b87d4009c8a3",
        "name": "Earth Search",
        "url": "https://earth-search.aws.element84.com/v0",
        "selected": False,
        "capability": None,
    },
    {
        "id": "aff201e0-58aa-483d-9e87-090c8baecd3c",
        "name": "Digital Earth Africa",
        "url": "https://explorer.digitalearth.africa/stac/",
        "selected": False,
        "capability": None,
    },
    {
        "id": "98c95473-9f32-4947-83b2-acc8bbf71f36",
        "name": "Radiant MLHub",
        "url": "https://api.radiant.earth/mlhub/v1/",
        "selected": False,
        "capability": None,
    },
    {
        "id": "17a79ce2-9a61-457d-926f-03d37c0606b6",
        "name": "NASA CMR STAC",
        "url": "https://cmr.earthdata.nasa.gov/stac",
        "selected": False,
        "capability": None,
    }
]

SITE = "https://stac-utils.github.io/qgis-stac-plugin/"
