"""Flood context: rain, terrain and permanent water. Facts only, never a level."""

import csv
import json
import math
from datetime import date
from pathlib import Path

import numpy as np
import pytest

rasterio = pytest.importorskip("rasterio", exc_type=ImportError)

from rasterio.transform import from_origin  # noqa: E402
from shapely.geometry import box, mapping  # noqa: E402

from landcheck.core import make_parcel  # noqa: E402
from landcheck.core.parcel import _reproject  # noqa: E402
from landcheck.modules import flood, flood_context as fc  # noqa: E402

X0, Y0 = 560000.0, 5050000.0  # EPSG:32635 metres near Pechea


def _parcel(dx=1500.0, dy=1500.0, size=60.0):
    utm = box(X0 + dx, Y0 - dy - size, X0 + dx + size, Y0 - dy)
    return make_parcel(_reproject(utm, 32635, 4326), buffer_m=100)


def _tif(path: Path, data: np.ndarray, dtype: str, nodata=None):
    with rasterio.open(path, "w", driver="GTiff", height=data.shape[0], width=data.shape[1], count=1,
                       dtype=dtype, crs="EPSG:32635", transform=from_origin(X0, Y0, 30, 30),
                       nodata=nodata) as ds:
        ds.write(data.astype(dtype), 1)


def _context(tmp: Path, parcel) -> Path:
    c = parcel.geom_wgs84.centroid
    cell = (round(round(c.x, 2), 3), round(round(c.y, 2), 3))
    with (tmp / fc.RAIN_FILE).open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time", "y", "x", "precipitation"])
        for d, mm in [(11, 0.0), (12, 17.0), (13, 1.0), (14, 30.0), (15, 2.0), (16, 31.0)]:
            w.writerow([f"2024-09-{d:02d}", cell[1], cell[0], mm])
            w.writerow([f"2024-09-{d:02d}", cell[1] + 0.5, cell[0] + 0.5, 99.0])  # far cell
    cols = np.arange(200)
    _tif(tmp / fc.DEM_FILE, np.tile(100 + 0.03 * 30 * cols, (200, 1)), "float32")  # 0.03 rise per metre
    jrc = np.zeros((200, 200), dtype="uint8")
    jrc[40:60, 40:60] = 90   # permanent water at 1200-1800 m east and south
    jrc[:, 0] = 255          # no data column
    _tif(tmp / fc.JRC_FILE, jrc, "uint8", nodata=255)
    fc._rain_grid.cache_clear()
    return tmp


def _dataset(root: Path) -> Path:
    """Tiny flood dataset: coverage 27.8-27.82 / 45.6-45.62, flooded square 27.805-27.810 / 45.605-45.610."""
    lid = "t_layer"
    (root / "layers").mkdir()
    (root / "manifest.json").write_text(json.dumps({"dataset_version": "v1", "method_version": "test", "layers": [
        {"layer_id": lid, "observation_date": "2024-09-15", "sensor": "PAZ"}]}))
    feat = lambda g, **k: {"type": "Feature", "properties": k.get("p", {}), "geometry": mapping(g)}  # noqa: E731
    (root / "coverage.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        feat(box(27.8, 45.6, 27.82, 45.62), p={"layer_id": lid})]}))
    (root / "layers" / f"{lid}.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        feat(box(27.805, 45.605, 27.810, 45.610))]}))
    flood._load.cache_clear()
    return root


def test_rain_sums_window_and_uses_nearest_cell(tmp_path):
    p = _parcel()
    d = _context(tmp_path, p)
    r = fc.rain(p, date(2024, 9, 15), d)
    assert r["total_mm"] == 50.0 and r["peak_day"] == "2024-09-14" and r["peak_day_mm"] == 30.0
    assert "50.0 mm" in fc.rain_sentence(r)


def test_rain_missing_dates_or_far_parcel_gives_none(tmp_path):
    p = _parcel()
    d = _context(tmp_path, p)
    assert fc.rain(p, date(2025, 1, 1), d) is None
    assert fc.rain(make_parcel(box(21.22, 45.75, 21.23, 45.755)), date(2024, 9, 15), d) is None


def test_terrain_slope_and_position(tmp_path):
    p = _parcel()
    t = fc.terrain(p, _context(tmp_path, p))
    assert abs(t["slope_deg"] - math.degrees(math.atan(0.03 * 30 / 30))) < 0.3
    assert 30 < t["percent_of_surroundings_lower"] < 70
    assert t["above_lowest_point_m"] > 0 and t["below_highest_point_m"] > 0


def test_permanent_water_detected_only_where_jrc_says(tmp_path):
    wet = _parcel(dx=1250, dy=1250, size=30)
    dry = _parcel(dx=3000, dy=3000)
    d = _context(tmp_path, wet)
    w = fc.permanent_water(wet, d)
    assert w["share_permanent_pct"] == 100.0 and fc.permanent_water_sentence(w)
    assert fc.permanent_water(dry, d)["share_permanent_pct"] == 0.0
    assert fc.permanent_water_sentence(fc.permanent_water(dry, d)) is None


def test_missing_files_give_empty_context(tmp_path):
    assert fc.describe(_parcel(), date(2024, 9, 15), tmp_path) == {}


def test_flood_result_gets_rain_sentence_and_context_but_same_level(tmp_path):
    p = make_parcel(box(27.806, 45.606, 27.808, 45.608))
    ctx = tmp_path / "ctx"
    ctx.mkdir()
    _context(ctx, p)
    root = tmp_path / "ds"
    root.mkdir()
    r = flood.flood_history(p, _dataset(root), ctx)
    assert r.level == "High" and "Rain in the 5 days" in r.summary
    assert r.details["context"]["rain"]["total_mm"] == 50.0
