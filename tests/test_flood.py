"""Flood module: observed, not observed, and no coverage (PRD Sections 8.1 and 8.2)."""

import json
from pathlib import Path

import pytest
from shapely.geometry import box, mapping, shape

from landcheck import pipeline
from landcheck.core import make_parcel
from landcheck.modules import flood

REAL = Path(__file__).resolve().parent.parent / "datasets" / "pilot-pechea" / "v1"


def _dataset(tmp_path: Path) -> Path:
    """Tiny dataset: coverage 0..0.02 deg, flooded square 0.005..0.010 (lon 27.8, lat 45.6)."""
    lon, lat = 27.8, 45.6
    cov = box(lon, lat, lon + 0.02, lat + 0.02)
    wet = box(lon + 0.005, lat + 0.005, lon + 0.010, lat + 0.010)
    lid = "t_layer"
    meta = {"layer_id": lid, "observation_date": "2024-09-15", "sensor": "PAZ"}
    (tmp_path / "layers").mkdir()
    (tmp_path / "manifest.json").write_text(json.dumps(
        {"dataset_version": "v1", "method_version": "test", "layers": [meta]}))
    (tmp_path / "coverage.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"layer_id": lid}, "geometry": mapping(cov)}]}))
    (tmp_path / "layers" / f"{lid}.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "id": "a", "properties": {}, "geometry": mapping(wet)}]}))
    flood._load.cache_clear()
    return tmp_path


def test_parcel_inside_flooded_zone_is_high(tmp_path):
    root = _dataset(tmp_path)
    r = flood.flood_history(make_parcel(box(27.806, 45.606, 27.808, 45.608)), root)
    assert r.level == "High" and r.value == 100.0 and r.unit == "% of parcel"
    assert r.sources[0].item_id == "t_layer"


def test_parcel_half_in_zone_reports_partial_share(tmp_path):
    root = _dataset(tmp_path)
    r = flood.flood_history(make_parcel(box(27.8095, 45.606, 27.8105, 45.608)), root)
    assert r.level == "High" and 45 < r.value < 55


def test_covered_but_not_flooded_is_unknown_not_low(tmp_path):
    root = _dataset(tmp_path)
    r = flood.flood_history(make_parcel(box(27.815, 45.615, 27.816, 45.616)), root)
    assert r.level == "Unknown" and "not mean" in r.summary and r.sources


def test_outside_coverage_is_no_coverage(tmp_path):
    root = _dataset(tmp_path)
    r = flood.flood_history(make_parcel(box(21.22, 45.75, 21.23, 45.755)), root)
    assert r.level == "Unknown" and r.summary.startswith("No coverage") and not r.sources


def test_missing_dataset_is_no_coverage(tmp_path):
    r = flood.flood_history(make_parcel(box(27.8, 45.6, 27.801, 45.601)), tmp_path / "nope")
    assert r.level == "Unknown"


def test_module_returns_both_risks_and_pipeline_still_works():
    results = pipeline.run(make_parcel(box(21.22, 45.75, 21.23, 45.755)))
    assert {r.risk for r in results} >= {"flood_history", "flood_susceptibility"}


@pytest.mark.skipif(not REAL.is_dir(), reason="pilot dataset not generated")
def test_real_pilot_dataset_flags_a_parcel_on_a_mapped_polygon():
    flood._load.cache_clear()
    fc = json.loads((REAL / "layers" / "flood_emsr758_aoi03_del_v1.geojson").read_text())
    inside = shape(fc["features"][0]["geometry"]).representative_point()
    parcel = make_parcel(box(inside.x - 1e-5, inside.y - 1e-5, inside.x + 1e-5, inside.y + 1e-5))
    r = flood.flood_history(parcel, REAL)
    assert r.level == "High" and r.value and r.value > 0
