"""Ground stability module. Owner: ______

Returns one result: "ground_stability" (vertical velocity in mm/year, negative = sinking).

Data: EGMS Ortho Level 3 radar points (100 m grid, 2020-2025), cut to the pilot zone by
landcheck.ingest.egms into a small CSV. Radar points exist only where the ground gives a stable
echo (buildings, roads, bare ground), so many parcels in fields have none.

Rules (PRD Section 8.1)
- No point within the search distance (the parcel buffer) -> "No coverage", NEVER "stable".
- Otherwise report the median vertical velocity of the points, how much they disagree, and how many
  there are. The level stays "Unknown": the thresholds in config/thresholds.yaml are placeholders
  with no documented method, and a risk class needs one. The measurement itself is shown.
- Confidence from the number of points and from how consistent neighbouring points are.

File: LANDCHECK_GROUND_PATH, else datasets/pilot-pechea/ground/egms_ortho_pechea_2020_2025.csv.
"""
from __future__ import annotations

import csv
import os
from datetime import date
from functools import lru_cache
from pathlib import Path

import numpy as np
import shapely

from landcheck.core import ModuleResult, Parcel, Source, no_coverage
from landcheck.core.config import thresholds
from landcheck.core.parcel import WGS84, _reproject

RISKS = ("ground_stability",)

DEFAULT_CSV = (Path(__file__).resolve().parents[2] / "datasets" / "pilot-pechea" / "ground"
               / "egms_ortho_pechea_2020_2025.csv")
SOURCE_ID = "egms-ortho-l3-2020-2025"
DATA_PERIOD = (date(2020, 12, 9), date(2025, 11, 25))  # first and last date of the time series
EPSG_3035 = 3035
METHOD_VERSION = "ground-egms-0.1"
SPREAD_OK_MM = 1.0    # interquartile range of neighbouring points, mm/year
SPREAD_MAX_MM = 2.0
MAX_IDS = 20


def csv_path() -> Path:
    env = os.environ.get("LANDCHECK_GROUND_PATH")
    return Path(env) if env else DEFAULT_CSV


@lru_cache(maxsize=2)
def _load(path: str) -> dict[str, np.ndarray]:
    rows = list(csv.DictReader(Path(path).open(newline="", encoding="utf-8")))

    def col(name: str) -> np.ndarray:
        return np.array([float(r[name]) if r[name] != "" else np.nan for r in rows], dtype=float)

    return {"pid": np.array([r["pid"] for r in rows]), "x": col("easting"), "y": col("northing"),
            "up": col("up_mm_yr"), "acc": col("up_acc"), "ew": col("ew_mm_yr")}


def _med(a: np.ndarray) -> float | None:
    a = a[~np.isnan(a)]
    return round(float(np.median(a)), 2) if a.size else None


def ground_stability(parcel: Parcel, path: Path | None = None) -> ModuleResult:
    path = path or csv_path()
    if not path.is_file():
        return no_coverage("ground_stability", f"EGMS point file not found at {path}")
    pts = _load(str(path))

    # Parcel + buffer in EPSG:3035, the CRS the EGMS points use.
    area = _reproject(parcel.area_wgs84, WGS84, EPSG_3035)
    inside = shapely.contains_xy(area, pts["x"], pts["y"])
    n = int(inside.sum())
    buffer_m = int(parcel.buffer_m)
    if n == 0:
        return no_coverage("ground_stability",
                           f"no EGMS radar points within {buffer_m} m of this parcel")

    up = pts["up"][inside]
    pids = [str(p) for p in pts["pid"][inside]]
    parcel_3035 = _reproject(parcel.geom_wgs84, WGS84, EPSG_3035)
    on_parcel = int(shapely.contains_xy(parcel_3035, pts["x"][inside], pts["y"][inside]).sum())
    q1, q3 = np.percentile(up, [25, 75])
    spread = round(float(q3 - q1), 2)
    median = round(float(np.median(up)), 2)
    min_points = int(thresholds()["ground"]["min_points"])

    if n >= 10 and spread <= SPREAD_OK_MM:
        confidence = "High"
    elif n >= min_points and spread <= SPREAD_MAX_MM:
        confidence = "Medium"
    else:
        confidence = "Low"

    text = (f"Radar points within {buffer_m} m of this parcel moved at a median of {median} mm/year "
            f"vertically (negative means sinking), from {n} point{'s' if n != 1 else ''}, "
            f"{DATA_PERIOD[0].year} to {DATA_PERIOD[1].year}.")
    if spread > SPREAD_MAX_MM:
        text += " Neighbouring points disagree, so treat this value with caution."
    if n < min_points:
        text += " There are very few points."
    return ModuleResult(
        risk="ground_stability", level="Unknown", value=median, unit="mm/year", confidence=confidence,
        summary=text,
        sources=[Source(collection="egms-ortho-l3", item_id=SOURCE_ID)],
        date_range=DATA_PERIOD, method_version=METHOD_VERSION,
        details={"points_in_buffer": n, "points_on_parcel": on_parcel, "buffer_m": buffer_m,
                 "vertical_median_mm_yr": median, "vertical_iqr_mm_yr": spread,
                 "vertical_min_max_mm_yr": [round(float(up.min()), 2), round(float(up.max()), 2)],
                 "east_west_median_mm_yr": _med(pts["ew"][inside]),
                 "acceleration_median_mm_yr2": _med(pts["acc"][inside]),
                 "point_ids": sorted(pids)[:MAX_IDS],
                 "note": "level is Unknown: no documented method for classes yet"})


def run(parcel: Parcel) -> list[ModuleResult]:
    return [ground_stability(parcel)]
