"""Flood module. Owner: ______

Returns two results:
  "flood_history"        - was this parcel mapped as flooded in the pilot dataset?
  "flood_susceptibility" - how likely, even if it never flooded (NOT built, out of MVP scope)

flood_history (this version)
- Reads the Copernicus EMS EMSR758 flood layers written by landcheck.ingest.cems
  (datasets/pilot-pechea/v1, or the folder in LANDCHECK_DATASET_DIR).
- For each layer, measures in the parcel's UTM zone:
    * how much of the parcel the satellite image covered, and
    * how much of the parcel was mapped as flooded.
- Rules (PRD Sections 8.1 and 8.2):
    * flooded area found            -> "High" (an observed fact, for that date only)
    * covered, but nothing mapped   -> "Unknown" ("not observed" is never "Low")
    * not covered by any image      -> "Unknown", no coverage

Context (landcheck.modules.flood_context): rain before the image (ANM), terrain (Copernicus DEM)
and permanent water (JRC) are added to details["context"]. They never change the level. Rain and
permanent water also add one plain sentence when the parcel was mapped as flooded.
"""
from __future__ import annotations

import json
import os
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from landcheck.core import ModuleResult, Parcel, Source, no_coverage
from landcheck.modules import flood_context
from landcheck.core.parcel import WGS84, _reproject

RISKS = ("flood_history", "flood_susceptibility")

COLLECTION = "cems-emsr758-aoi03"
DEFAULT_DATASET_DIR = Path(__file__).resolve().parents[2] / "datasets" / "pilot-pechea" / "v1"
MIN_AREA_M2 = 1.0  # overlaps smaller than 1 m2 are numerical noise, not flooding


def dataset_dir() -> Path:
    env = os.environ.get("LANDCHECK_DATASET_DIR")
    return Path(env) if env else DEFAULT_DATASET_DIR


@lru_cache(maxsize=4)
def _load(root: str) -> tuple[dict[str, Any], dict[str, BaseGeometry], dict[str, BaseGeometry]]:
    """(manifest, coverage by layer_id, flooded zones by layer_id), all in WGS84."""
    base = Path(root)
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    cov = json.loads((base / "coverage.geojson").read_text(encoding="utf-8"))
    coverage = {f["properties"]["layer_id"]: shape(f["geometry"]) for f in cov["features"]}
    zones: dict[str, BaseGeometry] = {}
    for meta in manifest["layers"]:
        lid = meta["layer_id"]
        fc = json.loads((base / "layers" / f"{lid}.geojson").read_text(encoding="utf-8"))
        zones[lid] = unary_union([shape(f["geometry"]) for f in fc["features"]])
    return manifest, coverage, zones


def _area_m2(geom: BaseGeometry, epsg: int) -> float:
    if geom.is_empty:
        return 0.0
    return _reproject(geom, WGS84, epsg).area


def _pct(part: float, whole: float) -> float:
    return round(100.0 * min(part / whole, 1.0), 1)


def _measure_layer(parcel: Parcel, meta: dict[str, Any], coverage: BaseGeometry,
                   zones: BaseGeometry) -> dict[str, Any]:
    total = parcel.geom_utm.area
    covered_m2 = _area_m2(parcel.geom_wgs84.intersection(coverage), parcel.epsg)
    flooded_m2 = _area_m2(parcel.geom_wgs84.intersection(zones), parcel.epsg)
    covered = covered_m2 >= MIN_AREA_M2
    flooded = flooded_m2 >= MIN_AREA_M2
    return {
        "layer_id": meta["layer_id"],
        "observation_date": meta["observation_date"],
        "sensor": meta["sensor"],
        "status": "observed" if flooded else ("not_observed" if covered else "no_coverage"),
        "covered_pct": _pct(covered_m2, total) if covered else 0.0,
        "flooded_pct": _pct(flooded_m2, total) if flooded else 0.0,
        "flooded_m2": round(flooded_m2, 1) if flooded else 0.0,
    }


def flood_history(parcel: Parcel, root: Path | None = None,
                  context_dir: Path | None = None) -> ModuleResult:
    root = root or dataset_dir()
    if not (root / "manifest.json").is_file():
        return no_coverage("flood_history", f"flood dataset not found at {root}")
    manifest, coverage, zones = _load(str(root))

    layers = [
        _measure_layer(parcel, meta, coverage[meta["layer_id"]], zones[meta["layer_id"]])
        for meta in manifest["layers"]
    ]
    seen = [x for x in layers if x["status"] != "no_coverage"]
    if not seen:
        return no_coverage("flood_history", "this parcel is outside the satellite images of the pilot flood")

    dates = [date.fromisoformat(x["observation_date"]) for x in seen]
    sources = [Source(collection=COLLECTION, item_id=x["layer_id"],
                      acquired=date.fromisoformat(x["observation_date"])) for x in seen]
    common = dict(sources=sources, date_range=(min(dates), max(dates)),
                  method_version=manifest["method_version"],
                  details={"layers": layers, "dataset_version": manifest["dataset_version"]})

    flooded = [x for x in seen if x["status"] == "observed"]
    worst = max(flooded, key=lambda x: x["flooded_pct"]) if flooded else None
    on = date.fromisoformat((worst or max(seen, key=lambda x: x["observation_date"]))["observation_date"])
    context = flood_context.describe(parcel, on, context_dir)
    if context:
        common["details"]["context"] = context
    if flooded:
        full = all(x["covered_pct"] >= 99.0 for x in seen)
        extra = [t for t in (flood_context.rain_sentence(context["rain"]) if "rain" in context else None,
                             flood_context.permanent_water_sentence(context["permanent_water"])
                             if "permanent_water" in context else None) if t]
        return ModuleResult(
            risk="flood_history", level="High", value=worst["flooded_pct"], unit="% of parcel",
            confidence="High" if full else "Medium",
            summary=(f"Flooding was mapped on {worst['flooded_pct']}% of this parcel on "
                     f"{worst['observation_date']} ({worst['sensor']}). It is one satellite image, "
                     "not the flood peak, and it says nothing about other floods."
                     + "".join(" " + t for t in extra)),
            **common)
    return ModuleResult(
        risk="flood_history", level="Unknown", value=None, unit=None, confidence="Low",
        summary=(f"No flooding was mapped on this parcel in the {len(seen)} satellite image(s) that "
                 "cover it. This does not mean the parcel is safe."),
        **common)


def flood_susceptibility(parcel: Parcel) -> ModuleResult:
    return ModuleResult(
        risk="flood_susceptibility", level="Unknown", value=None, unit=None, confidence="Low",
        summary="Not assessed: there is no susceptibility model in this version.")


def run(parcel: Parcel) -> list[ModuleResult]:
    return [flood_history(parcel), flood_susceptibility(parcel)]
