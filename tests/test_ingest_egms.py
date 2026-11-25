"""EGMS ingest: join, cut to the zone, cross-check against Explorer averages."""

import csv
import json
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import box, mapping

from landcheck.ingest import egms

T = Transformer.from_crs("EPSG:3035", "EPSG:4326", always_xy=True)
X0, Y0 = 5_690_050, 2_665_050  # grid cell centres near Pechea


def _tile(raw: Path, comp: str, vel: dict[str, float], xy: dict[str, tuple[int, int]]):
    d = raw / f"EGMS_L3_E56N26_100km_{comp}_2020_2025_1"
    d.mkdir(parents=True)
    cols = ["pid", "easting", "northing", "height_ortho", "rmse_ts", "mean_velocity", "mean_velocity_std",
            "acceleration", "acceleration_std", "seasonality", "seasonality_std",
            "gnss_velocity_n", "gnss_velocity_e", "gnss_velocity_u", "20201209"]
    with (d / f"{d.name}.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for pid, v in vel.items():
            x, y = xy[pid]
            w.writerow([pid, x, y, 50, 1, v, 0.1, 0.2, 0.1, 0, 0, 0, 0, 0, 0])


def _coverage(tmp: Path) -> Path:
    (lon0, lat0), (lon1, lat1) = T.transform(X0 - 400, Y0 - 400), T.transform(X0 + 400, Y0 + 400)
    p = tmp / "coverage.geojson"
    p.write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"layer_id": "x"}, "geometry": mapping(box(lon0, lat0, lon1, lat1))}]}))
    return p


def test_cuts_to_zone_joins_components_and_drops_far_points(tmp_path):
    xy = {"a": (X0, Y0), "b": (X0 + 100, Y0), "far": (X0 + 60_000, Y0)}
    _tile(tmp_path / "raw", "U", {"a": -1.0, "b": -3.0, "far": 5.0}, xy)
    _tile(tmp_path / "raw", "E", {"a": 0.5, "b": 1.5, "far": 9.0}, xy)
    out = tmp_path / "g" / "egms.csv"
    report = egms.run(tmp_path / "raw", _coverage(tmp_path), out, buffer_km=1.0)
    rows = list(csv.DictReader(out.open()))
    assert [r["pid"] for r in rows] == ["a", "b"]  # far point is outside the zone
    assert rows[0]["up_mm_yr"] == "-1.0" and rows[0]["ew_mm_yr"] == "0.5"
    assert 27 < float(rows[0]["lon"]) < 28 and 45 < float(rows[0]["lat"]) < 46
    assert report["points"] == 2 and out.with_name("egms.csv.ingest.json").is_file()


def test_cross_check_with_explorer_average(tmp_path):
    xy = {"a": (X0, Y0), "b": (X0 + 100, Y0)}
    _tile(tmp_path / "raw", "U", {"a": -1.0, "b": -3.0}, xy)
    _tile(tmp_path / "raw", "E", {"a": 0.0, "b": 0.0}, xy)
    avg = tmp_path / "avg.txt"
    avg.write_text(f"Name\tValue\nDataset\tVertical\nPoint ID\tAverage of 2 points\neasting\t{X0}\n"
                   f"northing\t{Y0}\nmean_velocity\t-2.1\nDATA\n20201209\t0\n")
    r = egms.run(tmp_path / "raw", _coverage(tmp_path), tmp_path / "o.csv", 1.0, [avg])
    c = r["cross_check_explorer_averages"][0]
    assert c["nearest_k_mean_velocity"] == -2.0 and c["difference_mm_yr"] == 0.1


def test_missing_component_fails_loudly(tmp_path):
    _tile(tmp_path / "raw", "U", {"a": -1.0}, {"a": (X0, Y0)})
    try:
        egms.run(tmp_path / "raw", _coverage(tmp_path), tmp_path / "o.csv", 1.0)
    except egms.IngestError:
        assert not (tmp_path / "o.csv").exists()
    else:
        raise AssertionError("expected IngestError")


def test_refuses_to_overwrite(tmp_path):
    out = tmp_path / "o.csv"
    out.write_text("x")
    try:
        egms.run(tmp_path, _coverage(tmp_path), out)
    except egms.IngestError:
        pass
    else:
        raise AssertionError("expected IngestError")
