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

## Testing

The plugin contains a bash script `run-tests.sh` in the root folder that can be used to run the 
all the plugin tests locally for QGIS 3.16 and 3.20 versions on a linux based OS.
The script uses the QGIS official docker images, in order to use it, docker images for QGIS version 3.16 and 3.20
need to be present.

Run the following commands in linux shell to pull the images and execute the script for tests.

```
docker pull qgis/qgis:release-3_16
docker pull qgis/qgis:release-3_22
```

Run the following command in linux shell to ensure the build directory exists and includes test files.

```
poetry run python admin.py build --tests
```

```
./run-tests.sh
```

GitHub actions workflow is provided by the plugin to run tests in QGIS 3.16, 3.18, 3.20 and 3.22 versions in 
the plugin repository, the workflow is located in the following directory `.github/workflow/ci.yml`


## Building documentation

Plugin uses a [mkdocs-material](https://squidfunk.github.io/mkdocs-material/) theme for the github pages documentation site,
to run locally the site run the following
commands after making updates to the documentation pages that are located inside the `docs` plugin folder.

```
poetry run mkdocs serve
```

This will create a local hosted site, that can be accessed via "localhost:8080".

For more options available via the `mkdocs` run the following commands.

```
poetry run mkdocs --help
```

or

```
poetry run mkdocs command --help
```
where command can be `serve` or `build`.

Whenever the poetry dependencies have changed, the poetry lock file should be updated and new packages should be installed.