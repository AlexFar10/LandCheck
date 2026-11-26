"""Analysis grid and the per-cell zone rule (issue #23, docs/LAYER_FORMAT.md)."""

import math

import numpy as np
import pytest
import shapely
import yaml
from pyproj import Transformer
from shapely.geometry import shape

from landcheck.grid import (
    DEFAULT_GRID_ID,
    GRID_CONFIG,
    CellResult,
    Grid,
    GridError,
    LayerInfo,
    cell_zone,
    grid_layer,
    load_grid,
)

TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32635", always_xy=True)
PECHEA_BBOX = (27.6159, 45.4607, 27.8670, 45.7384)  # PRD Section 5.1
CELL = "E560000_N5050000"  # near Pechea

LAYER = LayerInfo(
    layer_id="test_grid_layer",
    hazard_type="flood_history",
    observation_date="2024-09-15",
    source_name="Test source",
    source_url="https://example.org/source",
    method_version="test-0",
    dataset_version="t1",
    sample=True,
)


@pytest.fixture
def grid() -> Grid:
    return load_grid()


def test_default_grid_matches_config(grid):
    assert grid.grid_id == DEFAULT_GRID_ID == "galati-utm35n-200m-v1"
    assert grid.crs == "EPSG:32635"
    assert grid.cell_size_m == 200
    assert grid.shape == (453, 533)
    assert grid.min_valid_share == 0.5


def test_every_configured_grid_is_valid():
    grids = yaml.safe_load(GRID_CONFIG.read_text(encoding="utf-8"))["grids"]
    assert grids
    for grid_id in grids:
        load_grid(grid_id)


def test_extent_covers_the_pilot_and_galati_city(grid):
    west, south, east, north = PECHEA_BBOX
    for lon, lat in [(west, south), (east, north), (28.05, 45.43)]:
        grid.cell_id(*TO_UTM.transform(lon, lat))  # raises if outside


def test_cell_id_is_the_lower_left_corner(grid):
    assert grid.cell_id(560_123.4, 5_050_199.9) == CELL
    # Edges belong to the cell above and to the right: every point is in exactly one cell.
    assert grid.cell_id(560_200, 5_050_200) == "E560200_N5050200"
    assert grid.cell_origin(CELL) == (560_000, 5_050_000)


@pytest.mark.parametrize(
    "cell_id",
    [
        "560000_5050000",
        "E560000N5050000",
        "E-200_N5050000",
        "E560100_N5050000",
        "E400000_N5050000",
        "E560000_N5122800",
    ],
)
def test_bad_cell_ids_are_rejected(grid, cell_id):
    with pytest.raises(GridError):
        grid.cell_origin(cell_id)


def test_point_outside_the_extent_has_no_cell(grid):
    with pytest.raises(GridError, match="outside"):
        grid.cell_id(*TO_UTM.transform(26.5, 45.6))


def test_cell_geometry_is_a_200_m_square_in_wgs84(grid):
    geometry = grid.cell_geometry(CELL)
    ring = geometry["coordinates"][0]
    assert geometry["type"] == "Polygon"
    assert len(ring) == 5 and ring[0] == ring[-1]
    assert all(27 < lon < 28.5 and 45 < lat < 46.5 for lon, lat in ring)  # (lon, lat) order
    polygon = shape(geometry)
    assert polygon.exterior.is_ccw  # RFC 7946
    utm = shapely.transform(polygon, lambda c: np.column_stack(TO_UTM.transform(c[:, 0], c[:, 1])))
    assert utm.area == pytest.approx(40_000, rel=1e-3)
    assert utm.hausdorff_distance(grid.cell_box_m(CELL)) < 0.2  # 6-decimal rounding, ~0.1 m


def test_neighbouring_cells_share_exact_corners(grid):
    left = grid.cell_geometry("E560000_N5050000")["coordinates"][0]
    right = grid.cell_geometry("E560200_N5050000")["coordinates"][0]
    assert left[1] == right[0] and left[2] == right[3]


def test_cells_in_bbox_are_clipped_to_the_extent(grid):
    assert len(list(grid.cells_in_bbox_m((560_000, 5_050_000, 560_400, 5_050_600)))) == 6
    assert len(list(grid.cells_in_bbox_m((560_050, 5_050_050, 560_100, 5_050_100)))) == 1
    assert list(grid.cells_in_bbox_m((0, 0, 1000, 1000))) == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"cell_size_m": 0},
        {"extent_m": (511_401, 5_016_200, 602_000, 5_122_800)},
        {"extent_m": (602_000, 5_016_200, 511_400, 5_122_800)},
        {"min_valid_share": 0},
        {"min_valid_share": 1.5},
    ],
)
def test_invalid_grid_definitions_fail(kwargs):
    spec = {
        "grid_id": "bad",
        "crs": "EPSG:32635",
        "cell_size_m": 200,
        "extent_m": (511_400, 5_016_200, 602_000, 5_122_800),
        "min_valid_share": 0.5,
    } | kwargs
    with pytest.raises(GridError):
        Grid(**spec)


def test_unknown_grid_id_fails():
    with pytest.raises(GridError, match="Unknown grid_id"):
        load_grid("no-such-grid")


# Cell rule


def test_cell_zone_has_the_section_12_2_fields(grid):
    result = CellResult(CELL, "observed", valid_share=1.0, measurement=37.5, unit="%")
    feature = cell_zone(grid, LAYER, result)
    assert feature is not None
    assert feature["id"] == f"test_grid_layer-{CELL}"
    assert feature["geometry"] == grid.cell_geometry(CELL)
    assert feature["properties"] == {
        "layer_id": "test_grid_layer",
        "hazard_type": "flood_history",
        "classification": None,
        "measurement": 37.5,
        "unit": "%",
        "observation_date": "2024-09-15",
        "source_name": "Test source",
        "source_url": "https://example.org/source",
        "coverage_status": "observed",
        "method_version": "test-0",
        "dataset_version": "t1",
        "sample": True,
    }


def test_cell_with_too_little_valid_data_is_left_out(grid):
    assert cell_zone(grid, LAYER, CellResult(CELL, "not_observed", valid_share=0.49)) is None
    assert cell_zone(grid, LAYER, CellResult(CELL, "not_observed", valid_share=0.5)) is not None


@pytest.mark.parametrize(
    ("result", "message"),
    [
        (CellResult(CELL, "no_coverage", 1.0), "observed or not_observed"),  # type: ignore[arg-type]
        (CellResult(CELL, "not_assessed", 1.0), "observed or not_observed"),  # type: ignore[arg-type]
        (CellResult(CELL, "not_observed", 1.0, measurement=0.0, unit="%"), "not_observed"),
        (CellResult(CELL, "not_observed", 1.0, classification="Dry"), "not_observed"),
        (CellResult(CELL, "observed", 1.0, measurement=1.0), "unit is required"),
        (CellResult(CELL, "observed", 1.0, unit="%"), "unit without"),
        (CellResult(CELL, "observed", 1.0, measurement=math.nan, unit="%"), "not finite"),
        (CellResult(CELL, "observed", 1.2), "valid_share"),
    ],
)
def test_cell_results_that_break_the_format_fail(grid, result, message):
    with pytest.raises(GridError, match=message):
        cell_zone(grid, LAYER, result)


def test_grid_layer_coverage_is_the_union_of_its_zones(grid):
    results = [
        CellResult("E560200_N5050000", "observed", 1.0, measurement=10.0, unit="%"),
        CellResult("E560000_N5050000", "not_observed", 0.8),
        CellResult("E560400_N5050000", "not_observed", 0.2),  # left out
    ]
    features, coverage = grid_layer(grid, LAYER, results)
    assert [f["id"] for f in features] == [
        "test_grid_layer-E560000_N5050000",
        "test_grid_layer-E560200_N5050000",
    ]
    covered = shape(coverage)
    assert all(shape(f["geometry"]).within(covered.buffer(1e-9)) for f in features)
    assert not covered.intersects(shape(grid.cell_geometry("E560400_N5050000")).buffer(-1e-6))
    assert covered.geom_type == "Polygon"  # neighbours merge without slivers


def test_grid_layer_rejects_duplicates_and_empty_layers(grid):
    same = CellResult(CELL, "not_observed", 1.0)
    with pytest.raises(GridError, match="twice"):
        grid_layer(grid, LAYER, [same, same])
    with pytest.raises(GridError, match="empty"):
        grid_layer(grid, LAYER, [CellResult(CELL, "not_observed", 0.1)])
