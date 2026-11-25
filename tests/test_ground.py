"""Ground module: no points is no coverage, never stable (PRD Section 8.1)."""

import csv
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import box

from landcheck.core import make_parcel
from landcheck.modules import ground

T = Transformer.from_crs("EPSG:3035", "EPSG:4326", always_xy=True)
X0, Y0 = 5_690_050, 2_665_050


def _csv(tmp: Path, pts: list[tuple[int, int, float]]) -> Path:
    p = tmp / "g.csv"
    with p.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pid", "lon", "lat", "easting", "northing", "height_ortho_m", "up_mm_yr", "up_std",
                    "up_acc", "up_acc_std", "ew_mm_yr", "ew_std", "ew_acc", "ew_acc_std"])
        for i, (x, y, v) in enumerate(pts):
            w.writerow([f"p{i}", 0, 0, x, y, 50, v, 0.1, 0.2, 0.1, 0.3, 0.1, 0, 0])
    ground._load.cache_clear()
    return p


def _parcel(dx=0, dy=0, half=30.0):
    (lon0, lat0), (lon1, lat1) = (T.transform(X0 + dx - half, Y0 + dy - half),
                                  T.transform(X0 + dx + half, Y0 + dy + half))
    return make_parcel(box(lon0, lat0, lon1, lat1), buffer_m=300)


def test_many_consistent_points_give_high_confidence_but_unknown_level(tmp_path):
    pts = [(X0 + 100 * i, Y0 + 100 * j, -2.0 + 0.1 * (i % 2)) for i in range(-2, 3) for j in range(-2, 3)]
    r = ground.ground_stability(_parcel(), _csv(tmp_path, pts))
    assert r.level == "Unknown" and r.unit == "mm/year" and r.value == -2.0
    assert r.confidence == "High" and r.details["points_in_buffer"] == 25


def test_disagreeing_neighbours_lower_confidence_and_warn(tmp_path):
    pts = [(X0 + 100 * i, Y0, v) for i, v in enumerate([-8.0, 6.0, -7.0, 5.0])]
    r = ground.ground_stability(_parcel(), _csv(tmp_path, pts))
    assert r.confidence == "Low" and "disagree" in r.summary


def test_no_points_nearby_is_no_coverage_not_stable(tmp_path):
    r = ground.ground_stability(_parcel(), _csv(tmp_path, [(X0 + 5000, Y0, -1.0)]))
    assert r.level == "Unknown" and r.summary.startswith("No coverage") and r.value is None


def test_missing_file_is_no_coverage(tmp_path):
    assert ground.ground_stability(_parcel(), tmp_path / "x.csv").summary.startswith("No coverage")


def test_pipeline_parcel_far_away_still_unknown():
    from landcheck import pipeline
    res = pipeline.run(make_parcel(box(21.22, 45.75, 21.23, 45.755)))
    assert all(r.level == "Unknown" for r in res)
