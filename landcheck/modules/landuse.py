"""Land-use history module. Owner: ______

Returns one result: "land_use".

This version (summer NDVI only)
- Reads one NDVI value per summer (June-August) and year, 2018-2025, from a GeoTIFF with one band
  per year named NDVI_<year> (made with Earth Engine, see docs/GHID_DESCARCARE_DATE_PECHEA.md).
- For the parcel, takes the median NDVI of the pixels inside it, per year. Gaps stay gaps.
- It does NOT classify land use: one value per summer cannot tell a field from a forest, and a
  weak year can be drought, not a change of use. The level is always "Unknown" (PRD Section 8.1).
  Classification needs NDVI across the whole year (spring and autumn), planned for a later version.

Raster path: LANDCHECK_NDVI_PATH, else data/landuse/pechea_ndvi_vara_2018_2025.tif (not in git).
"""
from __future__ import annotations

import os
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

import numpy as np
from shapely.geometry import box, mapping

from landcheck.core import ModuleResult, Parcel, Source, no_coverage
from landcheck.core.parcel import WGS84, _reproject

RISKS = ("land_use",)

DEFAULT_RASTER = (Path(__file__).resolve().parents[2] / "data" / "landuse"
                  / "pechea_ndvi_vara_2018_2025.tif")
SOURCE_ID = "pechea_ndvi_vara_2018_2025"
LOW_NDVI = 0.2  # below this, vegetation is sparse (bare soil, roads, buildings, water)
METHOD_VERSION = "landuse-summer-ndvi-0.1"


def raster_path() -> Path:
    env = os.environ.get("LANDCHECK_NDVI_PATH")
    return Path(env) if env else DEFAULT_RASTER


@lru_cache(maxsize=2)
def _years(path: str) -> dict[int, int]:
    """band number (1-based) by year, from band names like NDVI_2018."""
    import rasterio

    with rasterio.open(path) as ds:
        found = {}
        for i, name in enumerate(ds.descriptions, start=1):
            m = re.fullmatch(r"NDVI_(\d{4})", name or "")
            if m:
                found[int(m.group(1))] = i
    return found


def _yearly_ndvi(parcel: Parcel, path: Path) -> tuple[dict[int, float | None], int, float] | None:
    """({year: median NDVI or None}, pixels used, share of parcel inside raster %) or None."""
    import rasterio
    from rasterio.mask import mask

    with rasterio.open(path) as ds:
        epsg = ds.crs.to_epsg()
        geom = parcel.geom_utm if parcel.epsg == epsg else _reproject(parcel.geom_wgs84, WGS84, epsg)
        inside = geom.intersection(box(*ds.bounds))
        if inside.is_empty or inside.area < 1.0:
            return None
        share = round(100.0 * inside.area / geom.area, 1)
        data, _ = mask(ds, [mapping(inside)], crop=True, all_touched=False, filled=True, nodata=np.nan)
        if np.isnan(data).all():  # parcel smaller than a pixel: take every pixel it touches
            data, _ = mask(ds, [mapping(inside)], crop=True, all_touched=True, filled=True, nodata=np.nan)
        pixels = int((~np.isnan(data[0])).sum())
        years = _years(str(path))
        out: dict[int, float | None] = {}
        for year, band in sorted(years.items()):
            vals = data[band - 1]
            vals = vals[~np.isnan(vals)]
            out[year] = round(float(np.median(vals)), 3) if vals.size else None
        return out, pixels, share


def land_use(parcel: Parcel, path: Path | None = None) -> ModuleResult:
    path = path or raster_path()
    if not path.is_file():
        return no_coverage("land_use", f"NDVI data not found at {path}")
    res = _yearly_ndvi(parcel, path)
    if res is None:
        return no_coverage("land_use", "this parcel is outside the NDVI data (Pechea pilot area)")
    series, pixels, share = res
    known = {y: v for y, v in series.items() if v is not None}
    details = {"summer_ndvi_by_year": series, "pixels_used": pixels,
               "parcel_inside_raster_pct": share, "pixel_size_m": 20}
    base = dict(risk="land_use", level="Unknown", confidence="Low", method_version=METHOD_VERSION,
                sources=[Source(collection="sentinel-2-l2a-summer-ndvi", item_id=SOURCE_ID)],
                details=details)
    if not known:
        return ModuleResult(value=None, unit=None,
                            summary="No usable summer vegetation data for this parcel.", **base)
    lo, hi = min(known.values()), max(known.values())
    first, last = min(known), max(known)
    text = (f"Summer vegetation (NDVI) on this parcel ranged from {lo:.2f} to {hi:.2f} "
            f"between {first} and {last}. Only summer is measured, so this does not show how "
            "the land was used.")
    if hi < LOW_NDVI:
        text += " Vegetation was sparse in every year."
    if share < 99.0:
        text += f" Only {share}% of the parcel is inside the data."
    return ModuleResult(value=round(float(np.median(list(known.values()))), 3),
                        unit="median summer NDVI",
                        date_range=(date(first, 6, 1), date(last, 8, 31)),
                        summary=text, **base)


def run(parcel: Parcel) -> list[ModuleResult]:
    return [land_use(parcel)]
