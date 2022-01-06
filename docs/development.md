---
hide:
  - navigation
---
  
## Install instructions

* Fork the repository [https://github.com/stac-utils/qgis-stac-plugin](https://github.com/stac-utils/qgis-stac-plugin)
* Clone the repository locally:

        git clone https://github.com/stac-utils/qgis-stac-plugin.git

Install poetry:

Poetry is a python dependencies management tool see [https://python-poetry.org/docs/#installation](https://python-poetry.org/docs/#installation) then using the poetry tool, update the poetry lock file and install plugin dependencies by running

     cd qgis-stac-plugin

     poetry update --lock

     poetry install

## Install the plugin into QGIS

Use the below command to install the plugin into QGIS 

    poetry run python admin.py install
