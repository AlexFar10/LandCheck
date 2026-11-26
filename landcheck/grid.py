"""Analysis grid and the rule that turns per-cell module results into zones.

The format is documented in docs/LAYER_FORMAT.md. Grids are defined in config/grid.yaml.

A cell is a square in the grid's metric CRS whose lower-left corner is a multiple of the cell
size. Its ID is that corner in metres, `E{x}_N{y}`, so IDs are stable whatever the extent.
The zone for a cell has the ID `{layer_id}-{cell_id}` and the cell polygon in WGS84.
"""

import math
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pyproj import Transformer
from shapely.geometry import box, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

GRID_CONFIG = Path(__file__).resolve().parents[1] / "config" / "grid.yaml"
DEFAULT_GRID_ID = "galati-utm35n-200m-v1"
# 6 decimals is about 0.1 m. Shared corners of neighbouring cells round to the same value.
COORD_DECIMALS = 6

_CELL_ID = re.compile(r"^E(\d+)_N(\d+)$")

# A stored zone only ever says what the source saw. no_coverage and not_assessed are never
# stored: the API derives them from the layer coverage and from missing layers (PRD 8.2).
StoredStatus = Literal["observed", "not_observed"]


class GridError(ValueError):
    """A cell or grid definition is invalid."""


@dataclass(frozen=True)
class Grid:
    grid_id: str
    crs: str
    cell_size_m: int
    extent_m: tuple[int, int, int, int]
    min_valid_share: float

    def __post_init__(self) -> None:
        size = self.cell_size_m
        if size <= 0:
            raise GridError(f"{self.grid_id}: cell_size_m must be positive")
        min_x, min_y, max_x, max_y = self.extent_m
        if any(v % size for v in self.extent_m) or not (min_x < max_x and min_y < max_y):
            raise GridError(f"{self.grid_id}: extent_m must be ordered multiples of {size}")
        if not 0 < self.min_valid_share <= 1:
            raise GridError(f"{self.grid_id}: min_valid_share must be in (0, 1]")

    @property
    def shape(self) -> tuple[int, int]:
        """(columns, rows) in the extent."""
        min_x, min_y, max_x, max_y = self.extent_m
        return (max_x - min_x) // self.cell_size_m, (max_y - min_y) // self.cell_size_m

    def cell_id(self, x: float, y: float) -> str:
        """ID of the cell that contains the metric point (x, y). Edges belong to the cell above
        and to the right, so every point is in exactly one cell."""
        size = self.cell_size_m
        cx, cy = math.floor(x / size) * size, math.floor(y / size) * size
        cell = f"E{cx}_N{cy}"
        self.cell_origin(cell)  # checks the extent
        return cell

    def cell_origin(self, cell_id: str) -> tuple[int, int]:
        """Lower-left corner of a cell in metres. Rejects malformed IDs and cells outside."""
        match = _CELL_ID.match(cell_id)
        if not match:
            raise GridError(f"Invalid cell id {cell_id!r}, expected E<x>_N<y>")
        x, y = int(match[1]), int(match[2])
        if x % self.cell_size_m or y % self.cell_size_m:
            raise GridError(f"Cell {cell_id} is not on the {self.cell_size_m} m grid")
        min_x, min_y, max_x, max_y = self.extent_m
        if not (min_x <= x < max_x and min_y <= y < max_y):
            raise GridError(f"Cell {cell_id} is outside grid {self.grid_id}")
        return x, y

    def cell_box_m(self, cell_id: str) -> BaseGeometry:
        """The cell in the grid's metric CRS."""
        x, y = self.cell_origin(cell_id)
        return box(x, y, x + self.cell_size_m, y + self.cell_size_m)

    def cell_geometry(self, cell_id: str) -> dict[str, Any]:
        """The cell as an RFC 7946 Polygon in WGS84 (lon, lat), counter-clockwise."""
        x, y = self.cell_origin(cell_id)
        s = self.cell_size_m
        corners = [(x, y), (x + s, y), (x + s, y + s), (x, y + s), (x, y)]
        to_wgs84 = _transformer(self.crs, "EPSG:4326")
        ring = []
        for cx, cy in corners:
            lon, lat = to_wgs84.transform(cx, cy)
            ring.append([round(lon, COORD_DECIMALS), round(lat, COORD_DECIMALS)])
        return {"type": "Polygon", "coordinates": [ring]}

    def cells_in_bbox_m(self, bounds: tuple[float, float, float, float]) -> Iterator[str]:
        """IDs of the cells that intersect a metric bounding box, clipped to the extent."""
        size = self.cell_size_m
        min_x, min_y, max_x, max_y = self.extent_m
        x0 = max(min_x, math.floor(bounds[0] / size) * size)
        y0 = max(min_y, math.floor(bounds[1] / size) * size)
        x1 = min(max_x, math.ceil(bounds[2] / size) * size)
        y1 = min(max_y, math.ceil(bounds[3] / size) * size)
        for y in range(y0, y1, size):
            for x in range(x0, x1, size):
                yield f"E{x}_N{y}"


@lru_cache(maxsize=8)
def _transformer(src: str, dst: str) -> Transformer:
    return Transformer.from_crs(src, dst, always_xy=True)


@lru_cache(maxsize=8)
def load_grid(grid_id: str = DEFAULT_GRID_ID, path: Path = GRID_CONFIG) -> Grid:
    grids = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("grids") or {}
    if grid_id not in grids:
        raise GridError(f"Unknown grid_id {grid_id!r} in {path}")
    spec = grids[grid_id]
    return Grid(
        grid_id=grid_id,
        crs=str(spec["crs"]),
        cell_size_m=int(spec["cell_size_m"]),
        extent_m=tuple(int(v) for v in spec["extent_m"]),  # type: ignore[arg-type]
        min_valid_share=float(spec["min_valid_share"]),
    )


# Per-cell result -> zone


@dataclass(frozen=True)
class CellResult:
    """What a module found in one cell, before it becomes a zone.

    observed:     the source detected or measured the hazard in this cell.
    not_observed: the source looked here and detected nothing (detection layers only, such as
                  flood extent). A measurement layer with no valid measurement in a cell must
                  NOT use not_observed: leave the cell out, so it reads as no_coverage.
    valid_share:  share of the cell covered by the source's valid data, 0-1.
    """

    cell_id: str
    status: StoredStatus
    valid_share: float
    classification: str | None = None
    measurement: float | None = None
    unit: str | None = None


@dataclass(frozen=True)
class LayerInfo:
    """The layer fields every zone repeats (PRD 12.2)."""

    layer_id: str
    hazard_type: str
    observation_date: str
    source_name: str
    source_url: str
    method_version: str
    dataset_version: str
    sample: bool


def cell_zone(grid: Grid, layer: LayerInfo, result: CellResult) -> dict[str, Any] | None:
    """Apply the cell rule. Returns the zone Feature, or None when the cell is left out because
    too little of it has valid data. Raises GridError on a result that breaks the format."""
    where = f"{layer.layer_id} cell {result.cell_id}"
    if result.status not in ("observed", "not_observed"):
        raise GridError(f"{where}: status must be observed or not_observed")
    if not 0 <= result.valid_share <= 1:
        raise GridError(f"{where}: valid_share must be between 0 and 1")
    if result.measurement is not None:
        if not math.isfinite(result.measurement):
            raise GridError(f"{where}: measurement is not finite")
        if not result.unit:
            raise GridError(f"{where}: unit is required when measurement exists")
    elif result.unit is not None:
        raise GridError(f"{where}: unit without a measurement")
    if result.status == "not_observed" and (
        result.classification is not None or result.measurement is not None
    ):
        raise GridError(f"{where}: not_observed cells carry no classification or measurement")
    if result.valid_share < grid.min_valid_share:
        return None
    return {
        "type": "Feature",
        "id": f"{layer.layer_id}-{result.cell_id}",
        "geometry": grid.cell_geometry(result.cell_id),
        "properties": {
            "layer_id": layer.layer_id,
            "hazard_type": layer.hazard_type,
            "classification": result.classification,
            "measurement": result.measurement,
            "unit": result.unit,
            "observation_date": layer.observation_date,
            "source_name": layer.source_name,
            "source_url": layer.source_url,
            "coverage_status": result.status,
            "method_version": layer.method_version,
            "dataset_version": layer.dataset_version,
            "sample": layer.sample,
        },
    }


def grid_layer(
    grid: Grid, layer: LayerInfo, results: Iterable[CellResult]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Zones for one grid layer, sorted by ID, and the layer coverage: the union of the cells
    that became zones. Coverage and zones therefore always agree."""
    features: dict[str, dict[str, Any]] = {}
    for result in results:
        feature = cell_zone(grid, layer, result)
        if feature is None:
            continue
        if feature["id"] in features:
            raise GridError(f"{layer.layer_id}: cell {result.cell_id} appears twice")
        features[feature["id"]] = feature
    if not features:
        raise GridError(f"{layer.layer_id}: no cell has enough valid data, the layer is empty")
    ordered = [features[k] for k in sorted(features)]
    coverage = unary_union([shape(f["geometry"]) for f in ordered])
    return ordered, mapping(coverage)
