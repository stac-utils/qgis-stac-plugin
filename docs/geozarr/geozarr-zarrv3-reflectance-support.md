# GeoZarr (Zarr v3) reflectance support

## Tested environment

- QGIS: 3.44.6-Solothurn
- GDAL: 3.13.0dev-e878b5b406-dirty (released 2026/01/03)

Zarr v3 sharding and HTTP range behavior can vary by GDAL version; this feature is implemented conservatively to reduce unnecessary reads and make failures less disruptive.

## Goal

Add experimental support for Zarr v3/GeoZarr reflectance assets so the plugin can:

- add a fast preview layer (tiles) for immediate visualization,
- add a “data” layer backed by a GDAL VRT for value inspection,
- keep preview and data aligned spatially,
- avoid expensive auto-stats and unnecessary network reads.

## UX

- If an item exposes an XYZ tiles link and a reflectance Zarr asset, the plugin adds:
  - `Surface Reflectance (preview)` (XYZ tiles)
  - `Surface Reflectance (data)` (GeoZarr VRT), added hidden by default

## Implementation highlights

### GeoZarr VRT

- Builds a single-resolution VRT with separate bands.
- Tries common reflectance resolutions (r10m/r20m/r60m) when auto-selecting.

### Georeferencing

- Injects `SRS` and `GeoTransform` into the VRT.
- Supports STAC `proj:transform` with 6 values (GDAL GeoTransform).

### Performance notes

- Avoids eager pixel reads during background creation (which can trigger expensive shard fetches).

### Visualization defaults

- Uses true-color mapping for reflectance: `b04/b03/b02`.
- Applies explicit per-channel stretch ranges to avoid NaN min/max from auto-stats:
  - float reflectance: 0..1
  - scaled integer reflectance: 0..10000

## Credentials

No secrets are embedded. If authentication becomes necessary for a STAC endpoint, prefer QGIS Auth Manager; only fall back to documented environment variables.
