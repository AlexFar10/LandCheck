"""Shared layer format: writing and strict loading of datasets (issue #23)."""

import json
import shutil
from pathlib import Path

import pytest

from landcheck.api.config import SAMPLE_DATASET_DIR
from landcheck.api.dataset import DatasetError, load_dataset
from landcheck.dataset_files import (
    DatasetWriteError,
    LayerFiles,
    canonical_json,
    sha256,
    write_dataset,
)
from landcheck.grid import CellResult, LayerInfo, grid_layer, load_grid

SOURCE_URL = "https://example.org/source"
VECTOR = "test_vector_v0"
CELLS = "test_cells_v0"

MANIFEST = {
    "dataset_id": "test-dataset",
    "dataset_version": "t1",
    "method_version": "test-ingest-0",
    "sample": True,
    "created_at": "2026-11-26T00:00:00Z",
    "code_commit": "0" * 40,
    "pilot_crs_metric": "EPSG:32635",
}


def layer_meta(layer_id: str, hazard_type: str, **extra) -> dict:
    return {
        "layer_id": layer_id,
        "title": f"TEST DATA {layer_id}",
        "hazard_type": hazard_type,
        "default_visible": False,
        "observation_date": "2024-09-15",
        "sensor": None,
        "source_name": "Test source",
        "source_url": SOURCE_URL,
        "attribution": "Test",
        "meaning": "Test layer.",
        "limitations": ["Test data."],
        "legend": [],
        **extra,
    }


def vector_layer() -> LayerFiles:
    square = [[27.74, 45.60], [27.75, 45.60], [27.75, 45.61], [27.74, 45.61], [27.74, 45.60]]
    coverage = [[27.70, 45.55], [27.90, 45.55], [27.90, 45.70], [27.70, 45.70], [27.70, 45.55]]
    feature = {
        "type": "Feature",
        "id": f"{VECTOR}-0001",
        "geometry": {"type": "Polygon", "coordinates": [square]},
        "properties": {
            "layer_id": VECTOR,
            "hazard_type": "flood_history",
            "classification": "Flooded area",
            "measurement": None,
            "unit": None,
            "observation_date": "2024-09-15",
            "source_name": "Test source",
            "source_url": SOURCE_URL,
            "coverage_status": "observed",
            "method_version": "test-ingest-0",
            "dataset_version": "t1",
            "sample": True,
        },
    }
    meta = layer_meta(
        VECTOR,
        "flood_history",
        acquired_at_as_published="2024-09-15T15:59:00",
        source_package="TEST_PACKAGE.zip",
        source_package_sha256="a" * 64,
        source_layer="observedEventA",
        invalid_geometries_repaired=0,
        area_ha_before_repair=1.0,
        area_ha_after_repair=1.0,
        provenance={"note": "anything else the ingest records"},
    )
    return LayerFiles(meta, {"type": "Polygon", "coordinates": [coverage]}, [feature])


def cell_layer() -> LayerFiles:
    grid = load_grid()
    info = LayerInfo(
        CELLS,
        "ground_stability",
        "2024-09-15",
        "Test source",
        SOURCE_URL,
        "test-cells-0",
        "t1",
        True,
    )
    results = [
        CellResult("E560000_N5050000", "observed", 1.0, measurement=-1.5, unit="mm/year"),
        CellResult("E560200_N5050000", "observed", 0.7, measurement=0.4, unit="mm/year"),
    ]
    features, coverage = grid_layer(grid, info, results)
    meta = layer_meta(
        CELLS, "ground_stability", method_version="test-cells-0", grid_id=grid.grid_id
    )
    return LayerFiles(meta, coverage, features)


@pytest.fixture
def root(tmp_path) -> Path:
    path = tmp_path / "t1"
    write_dataset(path, MANIFEST, [vector_layer(), cell_layer()])
    return path


def rewrite_layer(root: Path, layer_id: str, change) -> None:
    """Change a layer file and update its manifest checksum, so only the change is tested."""
    path = root / "layers" / f"{layer_id}.geojson"
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data["features"])
    raw = canonical_json(data)
    path.write_bytes(raw)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["layers"]:
        if entry["layer_id"] == layer_id:
            entry["output_sha256"] = sha256(raw)
            entry["feature_count"] = len(data["features"])
    (root / "manifest.json").write_bytes(canonical_json(manifest))


def rewrite_manifest(root: Path, change) -> None:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    change(manifest)
    (root / "manifest.json").write_bytes(canonical_json(manifest))


def props(index: int = 0, **values):
    def change(features):
        features[index]["properties"].update(values)

    return change


# Writing and loading


def test_written_dataset_loads_with_both_layer_kinds(root):
    dataset = load_dataset(root)
    assert set(dataset.layers) == {VECTOR, CELLS}
    assert len(dataset.layers[VECTOR].zones) == 1
    assert [z.id for z in dataset.layers[CELLS].zones] == [
        f"{CELLS}-E560000_N5050000",
        f"{CELLS}-E560200_N5050000",
    ]
    manifest = dataset.manifest
    assert manifest.method_version_of(dataset.layers[VECTOR].meta) == "test-ingest-0"
    assert manifest.method_version_of(dataset.layers[CELLS].meta) == "test-cells-0"
    assert dataset.layers[VECTOR].meta.provenance == {"note": "anything else the ingest records"}


def test_writer_is_byte_identical_across_runs(tmp_path, root):
    again = tmp_path / "again"
    write_dataset(again, MANIFEST, [vector_layer(), cell_layer()])
    files = sorted(p.relative_to(root) for p in root.rglob("*") if p.is_file())
    assert files == sorted(p.relative_to(again) for p in again.rglob("*") if p.is_file())
    for rel in files:
        assert (root / rel).read_bytes() == (again / rel).read_bytes()


def test_writer_never_overwrites_a_version(root):
    with pytest.raises(DatasetWriteError, match="not empty"):
        write_dataset(root, MANIFEST, [vector_layer()])


def test_writer_computes_counts_and_checksums_itself(tmp_path):
    layer = vector_layer()
    layer.meta["output_sha256"] = "0" * 64
    with pytest.raises(DatasetWriteError, match="computed"):
        write_dataset(tmp_path / "x", MANIFEST, [layer])


def test_bundled_sample_fixture_follows_the_format():
    dataset = load_dataset(SAMPLE_DATASET_DIR)
    assert dataset.manifest.sample is True


# Integrity (PRD 7.5 step 8, 12.7 checksum failure)


def test_changed_layer_file_fails_its_checksum(root):
    path = root / "layers" / f"{VECTOR}.geojson"
    path.write_bytes(path.read_bytes().replace(b"Flooded area", b"Flooded areA"))
    with pytest.raises(DatasetError, match="Checksum mismatch"):
        load_dataset(root)


def test_changed_coverage_file_fails_its_checksum(root):
    path = root / "coverage.geojson"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(DatasetError, match="Checksum mismatch"):
        load_dataset(root)


def test_feature_count_must_match(root):
    rewrite_manifest(root, lambda m: m["layers"][0].update(feature_count=5))
    with pytest.raises(DatasetError, match="manifest says 5"):
        load_dataset(root)


@pytest.mark.parametrize(
    "field", ["created_at", "code_commit", "pilot_crs_metric", "coverage_sha256"]
)
def test_prd_7_4_manifest_fields_are_required(root, field):
    rewrite_manifest(root, lambda m: m.pop(field))
    with pytest.raises(DatasetError, match=field):
        load_dataset(root)


def test_unknown_manifest_fields_are_rejected(root):
    rewrite_manifest(root, lambda m: m["layers"][0].update(area_ha_published_column=1.0))
    with pytest.raises(DatasetError, match="area_ha_published_column"):
        load_dataset(root)


# Zone values (PRD 8.2, 12.2)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (props(measurement=1.5), "unit is required"),
        (props(unit="ha"), "unit without"),
        (props(coverage_status="not_observed"), "not_observed zones carry no"),
        (props(coverage_status="no_coverage"), "coverage_status"),
        (props(coverage_status="not_assessed"), "coverage_status"),
        (props(sample=False), "sample does not match"),
        (props(observation_date="2024-09-14"), "observation_date does not match"),
        (props(source_name="Other"), "source_name does not match"),
        (props(source_url="https://example.org/other"), "source_url does not match"),
        (props(method_version="other-0"), "method_version does not match"),
        (props(hazard_type="land_use"), "hazard_type does not match"),
    ],
)
def test_zone_values_that_break_the_format_fail(root, change, message):
    rewrite_layer(root, VECTOR, change)
    with pytest.raises(DatasetError, match=message):
        load_dataset(root)


def test_not_observed_zone_without_values_loads(root):
    rewrite_layer(root, VECTOR, props(coverage_status="not_observed", classification=None))
    zone = load_dataset(root).layers[VECTOR].zones[0]
    assert zone.properties.coverage_status == "not_observed"


def test_zone_outside_its_coverage_fails(root):
    def move(features):
        ring = features[0]["geometry"]["coordinates"][0]
        features[0]["geometry"]["coordinates"][0] = [[x + 1.0, y] for x, y in ring]

    rewrite_layer(root, VECTOR, move)
    with pytest.raises(DatasetError, match="outside its layer coverage"):
        load_dataset(root)


# Grid layers


def test_grid_zone_must_have_its_cell_polygon(root):
    def shrink(features):
        ring = features[0]["geometry"]["coordinates"][0]
        ring[2] = [ring[2][0] - 0.0005, ring[2][1]]

    rewrite_layer(root, CELLS, shrink)
    with pytest.raises(DatasetError, match="not the polygon of its grid cell"):
        load_dataset(root)


@pytest.mark.parametrize(
    ("zone_id", "message"),
    [
        ("E560000_N5050000", "grid zone ids must be"),
        (f"{CELLS}-cell-1", "Invalid cell id"),
        (f"{CELLS}-E560100_N5050000", "not on the 200 m grid"),
    ],
)
def test_grid_zone_id_must_name_its_cell(root, zone_id, message):
    rewrite_layer(root, CELLS, lambda features: features[0].update(id=zone_id))
    with pytest.raises(DatasetError, match=message):
        load_dataset(root)


def test_unknown_grid_id_fails(root):
    rewrite_manifest(root, lambda m: m["layers"][1].update(grid_id="no-such-grid"))
    with pytest.raises(DatasetError, match="Unknown grid_id"):
        load_dataset(root)


# Layout


def test_layer_file_not_in_manifest_fails(root):
    (root / "layers" / "extra.geojson").write_text('{"features": []}', encoding="utf-8")
    with pytest.raises(DatasetError, match="do not match the manifest"):
        load_dataset(root)


def test_sample_fixture_copy_with_edited_layer_fails(tmp_path):
    copy = tmp_path / "sample"
    shutil.copytree(SAMPLE_DATASET_DIR, copy)
    path = copy / "layers" / "sample_flood_history_v0.geojson"
    path.write_text(
        path.read_text(encoding="utf-8").replace("observed", "not_observed"), encoding="utf-8"
    )
    with pytest.raises(DatasetError, match="Checksum mismatch"):
        load_dataset(copy)
