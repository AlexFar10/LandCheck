"""Tests for the CEMS ingest (PRD Section 7.5)."""

import shutil
from pathlib import Path

import pytest

pytest.importorskip("geopandas", exc_type=ImportError)

from shapely.geometry import Polygon  # noqa: E402

from landcheck.api.dataset import load_dataset  # noqa: E402
from landcheck.ingest import cems  # noqa: E402

RAW = Path(__file__).resolve().parent.parent / "data" / "cems"
needs_raw = pytest.mark.skipif(
    not all((RAW / s.package).is_file() for s in cems.LAYERS),
    reason="raw CEMS ZIPs not in data/cems (they are not stored in git)",
)


def test_bowtie_is_repaired_to_valid_polygons():
    bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])
    assert not bowtie.is_valid
    import geopandas as gpd

    gdf = gpd.GeoDataFrame({"area": [0.0]}, geometry=[bowtie], crs="EPSG:4326")
    geoms, stats = cems.repair(gdf)
    assert stats["invalid_geometries_repaired"] == 1
    assert geoms and all(g.is_valid for g in geoms)


def test_feature_id_is_deterministic_and_geometry_based():
    a = Polygon([(0, 0), (1, 0), (1, 1)])
    b = Polygon([(0, 0), (2, 0), (2, 2)])
    assert cems.feature_id("x", a) == cems.feature_id("x", a)
    assert cems.feature_id("x", a) != cems.feature_id("x", b)


def test_wrong_checksum_fails_loudly(tmp_path):
    spec = cems.LAYERS[0]
    (tmp_path / spec.package).write_bytes(b"not the real package")
    with pytest.raises(cems.IngestError):
        cems.verify_package(tmp_path, spec)


@needs_raw
def test_ingest_output_loads_in_api_and_is_byte_identical(tmp_path):
    first, second = tmp_path / "a" / "v1", tmp_path / "b" / "v1"
    cems.run(RAW, first)
    cems.run(RAW, second)

    ds = load_dataset(first)  # strict loader: any inconsistency raises
    counts = {lid: len(layer.zones) for lid, layer in ds.layers.items()}
    assert counts == {s.layer_id: s.expected_features for s in cems.LAYERS}

    for s in cems.LAYERS:
        name = Path("layers") / f"{s.layer_id}.geojson"
        assert (first / name).read_bytes() == (second / name).read_bytes()
    for name in ("manifest.json", "coverage.geojson"):
        assert (first / name).read_bytes() == (second / name).read_bytes()


@needs_raw
def test_refuses_to_overwrite_existing_version(tmp_path):
    out = tmp_path / "v1"
    out.mkdir()
    with pytest.raises(cems.IngestError):
        cems.run(RAW, out)


@needs_raw
def test_tampered_package_writes_nothing(tmp_path):
    raw = tmp_path / "raw"
    shutil.copytree(RAW, raw)
    victim = raw / cems.LAYERS[1].package
    victim.write_bytes(victim.read_bytes() + b"x")
    out = tmp_path / "out" / "v1"
    with pytest.raises(cems.IngestError):
        cems.run(raw, out)
    assert not out.exists()
