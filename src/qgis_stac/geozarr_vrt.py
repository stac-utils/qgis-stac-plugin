"""Helpers for loading GeoZarr / Zarr v3 reflectance into QGIS via GDAL.

This module intentionally stays conservative: it builds a simple single-resolution
VRT (separate bands) and injects georeferencing from STAC projection metadata when
available.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Sequence

from osgeo import gdal, osr


@dataclass(frozen=True)
class GeoZarrVrtSpec:
    reflectance_base_url: str
    name: str
    bands: tuple[str, ...] = ("b02", "b03", "b04", "b08")
    base_resolution: str = "auto"  # r10m|r20m|r60m|auto
    base_resolution_candidates: tuple[str, ...] = ("r10m", "r20m", "r60m")
    resampling: str = "near"
    vsi_prefix: str = "/vsicurl"
    epsg: int | None = None
    srs_wkt: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    geotransform: tuple[float, float, float, float, float, float] | None = None


def _inject_georeferencing(
    vrt_path: str,
    *,
    epsg: int | None,
    srs_wkt: str | None,
    bbox: tuple[float, float, float, float] | None,
    geotransform: tuple[float, float, float, float, float, float] | None,
    shape: tuple[int, int] | None,
) -> None:
    if (not epsg and not srs_wkt) or (not bbox and not geotransform):
        return

    ds = gdal.Open(vrt_path)
    if ds is None:
        return

    xsize = int(ds.RasterXSize or 0)
    ysize = int(ds.RasterYSize or 0)
    ds = None
    if xsize <= 0 or ysize <= 0:
        return

    if geotransform is not None:
        gt0, gt1, gt2, gt3, gt4, gt5 = geotransform
        if gt1 == 0.0 and gt5 == 0.0:
            return
        gt_text = f"{gt0}, {gt1}, {gt2}, {gt3}, {gt4}, {gt5}"
    else:
        minx, miny, maxx, maxy = bbox  # type: ignore[misc]
        px_w = (maxx - minx) / float(xsize)
        px_h = (maxy - miny) / float(ysize)
        if px_w == 0.0 or px_h == 0.0:
            return
        gt_text = f"{minx}, {px_w}, 0, {maxy}, 0, {-px_h}"

    wkt = None
    if srs_wkt and str(srs_wkt).strip():
        wkt = str(srs_wkt).strip()
    elif epsg:
        sr = osr.SpatialReference()
        sr.ImportFromEPSG(int(epsg))
        wkt = sr.ExportToWkt()

    if not wkt:
        return

    tree = ET.parse(vrt_path)
    root = tree.getroot()

    srs_el = root.find("SRS")
    if srs_el is None:
        srs_el = ET.Element("SRS")
        root.insert(0, srs_el)
    srs_el.text = wkt

    gt_el = root.find("GeoTransform")
    if gt_el is None:
        gt_el = ET.Element("GeoTransform")
        insert_at = 1 if root.find("SRS") is not None else 0
        root.insert(insert_at, gt_el)

    gt_el.text = gt_text

    tree.write(vrt_path, encoding="utf-8", xml_declaration=True)


_ZARR_MEDIA_TYPE_PREFIXES = (
    "application/vnd+zarr",
    "application/vnd.zarr",
)


def is_zarr_media_type(media_type: str | None) -> bool:
    if not media_type:
        return False
    mt = media_type.strip().lower()
    return any(prefix in mt for prefix in _ZARR_MEDIA_TYPE_PREFIXES)


def derive_reflectance_base(href: str) -> str | None:
    href = (href or "").strip()
    if not href:
        return None

    href = href.rstrip("/")

    if href.endswith("/measurements/reflectance"):
        return href

    if href.endswith("/measurements/reflectance/r10m"):
        return href[:-5]

    m = re.search(r"(/measurements/reflectance)(?:/r\d+m/[^/]+/zarr\.json)$", href)
    if m:
        return href[: m.end(1)]

    return None


def normalize_vsi_href(href: str, vsi_prefix: str = "/vsicurl") -> str:
    href = (href or "").strip()
    if not href:
        return href

    if href.startswith("/vsi"):
        return href

    if href.startswith("s3://"):
        # s3://bucket/key -> /vsis3/bucket/key
        return "/vsis3/" + href[len("s3://") :]

    if href.startswith("http://") or href.startswith("https://"):
        return f"{vsi_prefix.rstrip('/')}/{href}"

    return href


def _is_valid_resolution(res: str) -> bool:
    return bool(re.match(r"^r\d+m$", (res or "").strip().lower()))


def _build_vrt_for_resolution(
    *,
    ref_base: str,
    resolution: str,
    bands: Sequence[str],
    out_vrt: str,
    resampling: str,
    vsi_prefix: str,
) -> str:
    sources: list[str] = []
    for band in bands:
        src_href = f"{ref_base.rstrip('/')}/{resolution}/{band}/zarr.json"
        src = normalize_vsi_href(src_href, vsi_prefix=vsi_prefix)
        try:
            ds = gdal.Open(src)
        except Exception:
            ds = None
        if ds is None:
            continue
        ds = None
        sources.append(src)

    if not sources:
        raise RuntimeError(
            f"No readable Zarr band sources for {resolution} under {ref_base}"
        )

    options = gdal.BuildVRTOptions(separate=True, resampleAlg=resampling)
    vrt_ds = gdal.BuildVRT(out_vrt, sources, options=options)
    if vrt_ds is None:
        raise RuntimeError(f"Failed to build VRT for {resolution}")
    vrt_ds = None

    tree = ET.parse(out_vrt)
    root = tree.getroot()
    for idx, band_el in enumerate(root.findall("VRTRasterBand"), start=1):
        if idx > len(bands):
            break
        desc_el = band_el.find("Description")
        if desc_el is None:
            desc_el = ET.Element("Description")
            band_el.insert(0, desc_el)
        desc_el.text = bands[idx - 1]
    tree.write(out_vrt, encoding="utf-8", xml_declaration=True)

    return out_vrt


def build_multiscale_reflectance_vrt(spec: GeoZarrVrtSpec, out_dir: str) -> str:
    """Build a simple single-resolution VRT for reflectance bands.

    The function name is kept for backward compatibility with earlier iterations.
    """
    ref_base = spec.reflectance_base_url.strip()
    ref_base = ref_base.replace("/vsicurl/", "").replace("/vsicurl", "")
    ref_base = ref_base.rstrip("/")

    if not ref_base.endswith("/measurements/reflectance"):
        derived = derive_reflectance_base(ref_base)
        if derived:
            ref_base = derived

    name = re.sub(r"[^A-Za-z0-9._-]+", "_", spec.name).strip("_") or "scene"
    os.makedirs(out_dir, exist_ok=True)

    bands = tuple(b.lower() for b in spec.bands)
    for b in bands:
        if not re.match(r"^b[a-z0-9]+$", b):
            raise ValueError(f"Invalid band name: {b}")

    base_res = spec.base_resolution.strip().lower()
    if base_res != "auto" and not _is_valid_resolution(base_res):
        raise ValueError(f"Invalid base_resolution: {spec.base_resolution}")

    candidates = [
        c.strip().lower() for c in spec.base_resolution_candidates if c.strip()
    ]
    candidates = [c for c in candidates if _is_valid_resolution(c)] or [
        "r10m",
        "r20m",
        "r60m",
    ]
    if base_res != "auto":
        candidates = [base_res]

    last_err: Exception | None = None
    for res in candidates:
        out_vrt = os.path.join(out_dir, f"{name}_{res}.vrt")
        try:
            _build_vrt_for_resolution(
                ref_base=ref_base,
                resolution=res,
                bands=bands,
                out_vrt=out_vrt,
                resampling=spec.resampling,
                vsi_prefix=spec.vsi_prefix,
            )
            _inject_georeferencing(
                out_vrt,
                epsg=spec.epsg,
                srs_wkt=spec.srs_wkt,
                bbox=spec.bbox,
                geotransform=spec.geotransform,
                shape=None,
            )
            return out_vrt
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"Failed to build reflectance VRT for {ref_base}: {last_err}")


def build_multiscale_reflectance_vrt_temp(spec: GeoZarrVrtSpec) -> str:
    tmp_dir = tempfile.mkdtemp(prefix="qgis_stac_geozarr_")
    try:
        return build_multiscale_reflectance_vrt(spec, out_dir=tmp_dir)
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise


def build_multiscale_reflectance_vrt_cached(
    spec: GeoZarrVrtSpec, cache_root: str
) -> str:
    """Compatibility wrapper.

    The minimal implementation no longer maintains an on-disk cache; callers can
    add caching later if needed.
    """
    _ = cache_root
    return build_multiscale_reflectance_vrt_temp(spec)
