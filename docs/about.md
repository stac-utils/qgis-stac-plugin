---
hide:
  - navigation
---

## STAC

The SpatialTemporal Asset Catalog provides a standard way of describing and exposing geospatial data.
A 'spatiotemporal asset' is any file that represents information about the earth captured in a certain space and time.
See [https://stacspec.org/](https://stacspec.org/) for more information about the STAC specification.

## QGIS & STAC
At the moment of developing the STAC API Browser plugin, there was no other plugin available on the official QGIS 
plugin repository that fully supported using STAC API services inside QGIS.

However, there was a plugin called "STAC Browser" in the QGIS plugin repository, the plugin was not updated to use
the latest stable release of the STAC API and was not being actively maintained.

## External Libraries
The STAC API Browser uses a couple of external libraries to achieve its functionalities. The following are the libraries
used in the plugin.

- **PySTAC Client** a python package for working with STAC Catalogs and APIs that conform to the STAC and STAC API specs,
[https://pystac-client.readthedocs.io/en/latest/](https://pystac-client.readthedocs.io/en/latest/).
- **Planetary Computer** python library for interacting with Microsoft Planetary Computer STAC API services 
[https://pypi.org/project/planetary-computer/](https://pypi.org/project/planetary-computer/).
