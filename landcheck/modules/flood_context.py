"""Context for a flood result: rain before the image and the lie of the land (not a risk score).

Used by landcheck.modules.flood. Nothing here changes whether a parcel was flooded. It only adds
facts an analyst can read next to the result.

Data (datasets/pilot-pechea/context/, or LANDCHECK_CONTEXT_DIR)
- ploaie_grid_pechea_sep2024.csv: ANM daily rainfall grid, 0.01 degree cells, September 2024.
- pechea_dem_relief.tif: Copernicus DEM GLO-30 (30 m), EPSG:32635.
- pechea_jrc_occurrence_v1_5_eocube.tif: JRC Global Surface Water occurrence, % of time with water
  (0-100, 255 = no data), 30 m, EPSG:32635.
A missing file or a parcel outside the data gives None for that part, never an error.
"""
from __future__ import annotations

import csv
import math
import os
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from landcheck.core import Parcel
from landcheck.core.config import thresholds
from landcheck.core.parcel import WGS84, _reproject

DEFAULT_DIR = Path(__file__).resolve().parents[2] / "datasets" / "pilot-pechea" / "context"
RAIN_FILE = "ploaie_grid_pechea_sep2024.csv"
DEM_FILE = "pechea_dem_relief.tif"
JRC_FILE = "pechea_jrc_occurrence_v1_5_eocube.tif"
JRC_NODATA = 255
RAIN_WINDOW_DAYS = 5
MAX_CELL_DISTANCE_DEG = 0.01
LOCAL_RADIUS_M = 2000


def context_dir() -> Path:
    env = os.environ.get("LANDCHECK_CONTEXT_DIR")
    return Path(env) if env else DEFAULT_DIR


@lru_cache(maxsize=2)
def _rain_grid(path: str) -> dict[tuple[float, float], dict[date, float]]:
    grid: dict[tuple[float, float], dict[date, float]] = {}
    with Path(path).open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (round(float(r["x"]), 3), round(float(r["y"]), 3))
            grid.setdefault(key, {})[date.fromisoformat(r["time"])] = float(r["precipitation"])
    return grid


def rain(parcel: Parcel, on: date, directory: Path | None = None) -> dict[str, Any] | None:
    """Rain in the RAIN_WINDOW_DAYS ending on `on` (inclusive), from the grid cell nearest the parcel."""
    path = (directory or context_dir()) / RAIN_FILE
    if not path.is_file():
        return None
    grid = _rain_grid(str(path))
    c = parcel.geom_wgs84.centroid
    k = math.cos(math.radians(c.y))
    (cx, cy), days = min(grid.items(), key=lambda kv: math.hypot((kv[0][0] - c.x) * k, kv[0][1] - c.y))
    if math.hypot((cx - c.x) * k, cy - c.y) > MAX_CELL_DISTANCE_DEG:
        return None
    window = [on - timedelta(days=i) for i in range(RAIN_WINDOW_DAYS - 1, -1, -1)]
    if any(d not in days for d in window):
        return None
    daily = {d.isoformat(): round(days[d], 1) for d in window}
    peak = max(window, key=lambda d: days[d])
    return {"window_days": RAIN_WINDOW_DAYS, "ending": on.isoformat(),
            "total_mm": round(sum(days[d] for d in window), 1),
            "peak_day": peak.isoformat(), "peak_day_mm": round(days[peak], 1),
            "daily_mm": daily, "cell_lon": cx, "cell_lat": cy, "source": "ANM daily rainfall grid"}


def terrain(parcel: Parcel, directory: Path | None = None) -> dict[str, Any] | None:
    """Elevation, slope and position of the parcel against the land within LOCAL_RADIUS_M."""
    path = (directory or context_dir()) / DEM_FILE
    if not path.is_file():
        return None
    import rasterio
    from rasterio.features import geometry_mask
    from rasterio.windows import from_bounds

    with rasterio.open(path) as ds:
        epsg = ds.crs.to_epsg()
        geom = parcel.geom_utm if parcel.epsg == epsg else _reproject(parcel.geom_wgs84, WGS84, epsg)
        c = geom.centroid
        left, bottom, right, top = ds.bounds
        if not (left <= c.x <= right and bottom <= c.y <= top):
            return None
        r = LOCAL_RADIUS_M
        win = from_bounds(c.x - r, c.y - r, c.x + r, c.y + r, ds.transform).round_offsets().round_lengths()
        dem = ds.read(1, window=win, boundless=True, fill_value=np.nan).astype("float64")
        tr = ds.window_transform(win)
        px = abs(ds.res[0])
        yy, xx = np.mgrid[0:dem.shape[0], 0:dem.shape[1]]
        wx, wy = tr.c + (xx + 0.5) * tr.a, tr.f + (yy + 0.5) * tr.e  # pixel centres, north-up grid
        local = (np.hypot(wx - c.x, wy - c.y) <= r) & ~np.isnan(dem)
        on_parcel = ~geometry_mask([geom], out_shape=dem.shape, transform=tr, all_touched=True) & ~np.isnan(dem)
        if not on_parcel.any() or not local.any():
            return None
        gy, gx = np.gradient(dem, px)
        slope = np.degrees(np.arctan(np.hypot(gx, gy)))
        elev = float(np.median(dem[on_parcel]))
        around = dem[local]
        return {"elevation_m": round(elev, 1),
                "slope_deg": round(float(np.nanmedian(slope[on_parcel])), 1),
                "radius_m": r,
                "percent_of_surroundings_lower": round(100.0 * float((around < elev).mean()), 0),
                "above_lowest_point_m": round(elev - float(around.min()), 1),
                "below_highest_point_m": round(float(around.max()) - elev, 1),
                "pixel_size_m": int(px), "source": "Copernicus DEM GLO-30"}


def permanent_water(parcel: Parcel, directory: Path | None = None) -> dict[str, Any] | None:
    """How often JRC saw water on the parcel's pixels (permanent water = most of the time)."""
    path = (directory or context_dir()) / JRC_FILE
    if not path.is_file():
        return None
    import rasterio
    from rasterio.features import geometry_mask

    limit = float(thresholds()["flood"]["jrc_permanent_occurrence"])
    with rasterio.open(path) as ds:
        epsg = ds.crs.to_epsg()
        geom = parcel.geom_utm if parcel.epsg == epsg else _reproject(parcel.geom_wgs84, WGS84, epsg)
        left, bottom, right, top = ds.bounds
        c = geom.centroid
        if not (left <= c.x <= right and bottom <= c.y <= top):
            return None
        win = ds.window(*geom.bounds).round_offsets().round_lengths()
        data = ds.read(1, window=win, boundless=True, fill_value=JRC_NODATA)
        tr = ds.window_transform(win)
        under = ~geometry_mask([geom], out_shape=data.shape, transform=tr, all_touched=True) & (data != JRC_NODATA)
        if not under.any():
            return None
        vals = data[under].astype(float)
        return {"max_occurrence_pct": int(vals.max()),
                "share_permanent_pct": round(100.0 * float((vals >= limit).mean()), 0),
                "permanent_if_at_least_pct": limit, "pixel_size_m": int(abs(ds.res[0])),
                "source": "JRC Global Surface Water v1.5"}


def describe(parcel: Parcel, on: date, directory: Path | None = None) -> dict[str, Any]:
    """Everything available, keyed by part. Parts without data are left out."""
    out: dict[str, Any] = {}
    for name, fn in (("rain", lambda: rain(parcel, on, directory)),
                     ("terrain", lambda: terrain(parcel, directory)),
                     ("permanent_water", lambda: permanent_water(parcel, directory))):
        try:
            value = fn()
        except (ImportError, OSError, ValueError, KeyError):  # context is optional, never fatal
            value = None
        if value is not None:
            out[name] = value
    return out


def rain_sentence(r: dict[str, Any]) -> str:
    return (f"Rain in the {r['window_days']} days up to {r['ending']}: {r['total_mm']} mm "
            f"(most on {r['peak_day']}, {r['peak_day_mm']} mm).")


def permanent_water_sentence(w: dict[str, Any]) -> str | None:
    if w["share_permanent_pct"] <= 0:
        return None
    return (f"JRC shows water most of the time on about {w['share_permanent_pct']:.0f}% of this parcel, "
            "so the mapped water may be, at least in part, a river or pond and not flooding.")
