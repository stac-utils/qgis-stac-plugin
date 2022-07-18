# Changelog

## Released

### 1.1.0 2022-07-18
- Fix for footprints layer loading workflow
- Data driven filtering using STAC Queryables
- Multiple assets and footprints loading and downloading
- Minimizeable plugin main window
- Subscription key usage for SAS based connections
- Support for COPC layers
- Support for netCDF layers
- New collection dialog
- Auto assets loading after downloading assets
- Fixed connection dialog window title when in edit mode
- Fallback to overview when item thumbnail asset is not available
- Display selected collections
- Upgraded pystac-client library to 0.3.2
- Support for CQL2-JSON filter language
- Moved sort and order buttons to search tab

### 1.0.0 2022-01-13
- Fix for plugin UI lagging bug.
- Updates to loading and downloading assets workflow.
- Support for adding vector based assets eg. GeoJSON, GeoPackage
- Fix API page size now default is 10 items.
- Include extension in the downloaded files.
- Update UI with more descriptive tooltips.

## [Unreleased] 

### 1.0.0-pre 2022-01-11
- Changed loading and downloading assets workflow [#93](https://github.com/stac-utils/qgis-stac-plugin/pull/93).
- Implemented testing connection functionality.
- Reworked filter and sort features on the search item results.
- Fetch for STAC API conformance classes [#82](https://github.com/stac-utils/qgis-stac-plugin/pull/82).
- Added STAC API signing using SAS token [#79](https://github.com/stac-utils/qgis-stac-plugin/pull/79).
- Support for downloading assets and loading item footprints in QGIS, [#70](https://github.com/stac-utils/qgis-stac-plugin/pull/70).
- Enabled adding STAC item assets as map layers in QGIS [#58](https://github.com/stac-utils/qgis-stac-plugin/pull/58).
- Added plugin documentation in GitHub pages.

## [beta]

### 1.0.0-beta 2021-12-11
- Fixed slow item search.
- Updated plugin search result to include pagination [#51](https://github.com/stac-utils/qgis-stac-plugin/pull/51).
- Support for search result filtering and sorting [#47](https://github.com/stac-utils/qgis-stac-plugin/pull/47).
- Implemented search [#40](https://github.com/stac-utils/qgis-stac-plugin/pull/40).
- Added default configured STAC API catalogs [#26](https://github.com/stac-utils/qgis-stac-plugin/pull/26).
- Basic STAC API support [#17](https://github.com/stac-utils/qgis-stac-plugin/pull/17).
