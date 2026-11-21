"""Sentinel-2 helpers, shared by the land-use module and the optical part of floods.

Fixes the problems we found in the course notebook:
- scenes are chosen by date and clear-sky share over the parcel, not list position
- SCL cloud/shadow mask is always applied
- the +1000 offset (processing baseline >= 04.00, Jan 2022+) is removed per scene
- reads fail loudly (fail_on_error=True), never silently fill with nodata
- no forward-filling of missing months
"""
from __future__ import annotations

import re
from datetime import date

import numpy as np
import xarray as xr

from .output import Source
from .parcel import Parcel

DEFAULT_STAC = "https://stac.eocube.ro"
COLLECTION = "sentinel-2-l2a"

# Canonical band name -> asset keys seen in different catalogs (EOCube uses B03_10m etc.)
ASSET_ALIASES = {
    "blue":  ["B02_10m", "B02", "blue"],
    "green": ["B03_10m", "B03", "green"],
    "red":   ["B04_10m", "B04", "red"],
    "nir":   ["B08_10m", "B08", "nir"],
    "swir16": ["B11_20m", "B11", "swir16"],
    "swir22": ["B12_20m", "B12", "swir22"],
    "scl":   ["SCL_20m", "SCL", "scl"],
}

# SCL classes treated as not usable: no data, saturated, cloud shadow,
# cloud medium/high probability, thin cirrus.
SCL_INVALID = (0, 1, 3, 8, 9, 10)


# ---------- search & load ----------

def search(parcel: Parcel, start: str, end: str, stac_url: str = DEFAULT_STAC,
           collection: str = COLLECTION, max_scene_cloud: float = 80) -> list:
    """STAC search over the parcel area. Pagination is handled by pystac-client.

    max_scene_cloud is only a loose pre-filter (it's measured over the whole
    110 km tile); the real filter is clear_fraction() over the parcel.
    """
    from pystac_client import Client
    s = Client.open(stac_url).search(
        collections=[collection], intersects=parcel.area_wgs84.__geo_interface__,
        datetime=f"{start}/{end}", query={"eo:cloud_cover": {"lt": max_scene_cloud}},
    )
    return sorted(s.items(), key=lambda it: it.datetime)


def resolve_asset(item, band: str) -> str:
    """Canonical band name -> the asset key this item actually uses."""
    for key in ASSET_ALIASES[band]:
        if key in item.assets:
            return key
    raise KeyError(f"{item.id} has no asset for band '{band}'")


def load(items: list, parcel: Parcel, bands: list[str], resolution: int = 10) -> xr.Dataset:
    """Load bands over parcel + buffer on a UTM grid. Returns DNs (call to_reflectance next).

    Tiles from the same overpass are merged (groupby='solar_day').
    Variables are renamed to canonical names: red, nir, scl, ...
    """
    import odc.stac
    keys = {b: resolve_asset(items[0], b) for b in bands}
    for it in items[1:]:
        for b, k in keys.items():
            if k not in it.assets:
                raise KeyError(f"Inconsistent asset names: {it.id} lacks {k}")
    ds = odc.stac.load(
        items, bands=list(keys.values()), geopolygon=parcel.area_wgs84,
        crs=f"EPSG:{parcel.epsg}", resolution=resolution,
        groupby="solar_day", fail_on_error=True,
    )
    return ds.rename({v: k for k, v in keys.items()})


# ---------- radiometry & masking ----------

def offset_for_item(item) -> int:
    """DN offset to add before scaling: -1000 for baseline >= 04.00, else 0.

    Prefers the item's raster:bands metadata; falls back to the baseline in the ID
    (e.g. ..._N0511_... -> 05.11). Check on EOCube whether their COGs carry it.
    """
    for a in item.assets.values():
        rb = a.extra_fields.get("raster:bands")
        if rb and "offset" in rb[0] and rb[0].get("scale"):
            return int(round(rb[0]["offset"] / rb[0]["scale"]))
    baseline = item.properties.get("s2:processing_baseline")
    if baseline is None:
        m = re.search(r"_N(\d{4})_", item.id)
        if not m:
            raise ValueError(f"Can't determine processing baseline for {item.id}")
        baseline = f"{m.group(1)[:2]}.{m.group(1)[2:]}"
    return -1000 if float(baseline) >= 4.0 else 0


def to_reflectance(ds: xr.Dataset, offsets_by_date: dict[date, int]) -> xr.Dataset:
    """DN -> surface reflectance, applying each date's offset. SCL is left untouched."""
    out = ds.copy()
    days = [np.datetime64(t, "D").astype(object) for t in ds.time.values]
    off = xr.DataArray([offsets_by_date[d] for d in days], dims="time", coords={"time": ds.time})
    for v in ds.data_vars:
        if v != "scl":
            out[v] = ((ds[v].where(ds[v] > 0) + off) / 10_000).clip(min=0)
    return out


def offsets_by_date(items: list) -> dict[date, int]:
    return {it.datetime.date(): offset_for_item(it) for it in items}


def clear_mask(scl: xr.DataArray) -> xr.DataArray:
    """True where the pixel is usable (not cloud, shadow, cirrus, no data)."""
    return ~scl.isin(SCL_INVALID)


def clear_fraction(ds: xr.Dataset) -> xr.DataArray:
    """Share of clear pixels per date over the loaded area (parcel + buffer)."""
    return clear_mask(ds["scl"]).mean(dim=("y", "x"))


def select_clear(ds: xr.Dataset, min_clear: float = 0.8) -> xr.Dataset:
    """Keep dates with at least min_clear usable pixels, and mask the rest to NaN."""
    frac = clear_fraction(ds)
    ds = ds.sel(time=frac.time[frac >= min_clear])
    m = clear_mask(ds["scl"])
    return ds.assign({v: ds[v].where(m) for v in ds.data_vars if v != "scl"})


# ---------- indices ----------

def nd(a: xr.DataArray, b: xr.DataArray) -> xr.DataArray:
    """Normalized difference (a - b) / (a + b)."""
    return (a - b) / (a + b)

def ndvi(ds):  return nd(ds["nir"], ds["red"])
def mndwi(ds): return nd(ds["green"], ds["swir16"])
def nbr(ds):   return nd(ds["nir"], ds["swir22"])


# ---------- provenance ----------

def sources_from_items(items: list, collection: str = COLLECTION) -> list[Source]:
    return [Source(collection, it.id, it.datetime.date()) for it in items]
