# Shared layer format and cell grid

Every layer the API serves uses this format: the CEMS reference layers, our own Sentinel-1 flood
map, ground stability and land use. A module owner who follows it can add a layer without any
change to the API or the web app. Issue #23. PRD Sections 7.4, 8.2 and 12.2.

The format is enforced in code, not only described here:

| Part | Code |
|---|---|
| Manifest and zone models | `landcheck/api/models.py` (`Manifest`, `LayerMeta`, `ZoneProperties`) |
| Loader and its checks | `landcheck/api/dataset.py` (`load_dataset`) |
| Grid and the cell rule | `config/grid.yaml`, `landcheck/grid.py` |
| Writer with checksums | `landcheck/dataset_files.py` (`write_dataset`) |
| Tests | `tests/test_dataset.py`, `tests/test_grid.py` |

If this document and the code disagree, the code is what runs. Fix whichever is wrong in the same PR.

## 1. Dataset folder

```text
datasets/<dataset_id>/<dataset_version>/
├── manifest.json        dataset and layer metadata, provenance, checksums
├── coverage.geojson     one feature per layer: where that layer's source looked
└── layers/
    └── <layer_id>.geojson   one FeatureCollection of zones per layer
```

- A published version is immutable. Any data change makes a new version folder. `write_dataset` refuses to write into a folder that is not empty.
- Files are UTF-8 JSON. `write_dataset` writes canonical JSON (sorted keys, no spaces, one trailing newline), so the same input gives byte-identical files (PRD 7.5).
- `.gitattributes` keeps LF line endings, so checksums hold on Windows and Linux.
- Coordinates are WGS84 `(longitude, latitude)` (RFC 7946). Areas and distances are measured in the metric CRS, never in degrees.
- One dataset may hold layers from several modules.

## 2. `manifest.json`

### Dataset fields

| Field | Type | Notes |
|---|---|---|
| `dataset_id` | string | For example `pilot-pechea` |
| `dataset_version` | string | For example `v1`. Repeated in every zone |
| `method_version` | string | Default for layers that do not set their own |
| `sample` | bool | `true` for fixtures. Repeated in every zone and in `/health` |
| `created_at` | UTC timestamp | When the ingest ran |
| `code_commit` | string | Git commit of the ingest code |
| `pilot_crs_metric` | string | `EPSG:32635` for the pilot |
| `coverage_sha256` | hex SHA-256 | Of `coverage.geojson`, checked on load |
| `layers` | list | Layer entries below |

### Layer fields

| Group | Field | Type | Notes |
|---|---|---|---|
| Served by `/api/v1/layers` (PRD 12.4) | `layer_id` | string | Also the file name in `layers/` |
| | `title` | string | |
| | `hazard_type` | enum | `flood_history`, `flood_hazard_zone`, `ground_stability`, `land_use` |
| | `default_visible` | bool | |
| | `observation_date` | ISO date | One date per layer. Repeated in every zone |
| | `sensor` | string or null | |
| | `source_name`, `source_url` | string, URL | Repeated in every zone |
| | `attribution`, `meaning` | string | |
| | `limitations` | list of strings | |
| | `legend` | list of `{label, color}` | |
| Method | `method_version` | string or null | Overrides the dataset default. Repeated in every zone |
| Grid | `grid_id` | string or null | Set for grid layers (Section 5), null for source polygon layers |
| Integrity | `feature_count` | int | Checked against the file |
| | `output_sha256` | hex SHA-256 | Of `layers/<layer_id>.geojson`, checked on load |
| Provenance (PRD 7.4, not served) | `acquired_at_as_published` | string or null | Acquisition time as the source publishes it |
| | `source_package`, `source_package_sha256` | string or null | The pinned download |
| | `source_layer` | string or null | For example `observedEventA` |
| | `invalid_geometries_repaired` | int or null | |
| | `area_ha_before_repair`, `area_ha_after_repair` | number or null | Measured in the metric CRS |
| | `provenance` | object | Any other record the ingest keeps: input checksums, counts, parameters |

Unknown fields are rejected, so a typo never passes silently. Put anything extra under `provenance`.

## 3. Zone feature

One schema for all modules: the PRD 12.2 fields plus `layer_id`, `dataset_version` and `sample`.

```json
{
  "type": "Feature",
  "id": "<stable id>",
  "geometry": { "type": "Polygon", "coordinates": [[[27.74, 45.60], "..."]] },
  "properties": {
    "layer_id": "<layer_id>",
    "hazard_type": "flood_history",
    "classification": null,
    "measurement": null,
    "unit": null,
    "observation_date": "2024-09-15",
    "source_name": "<source name>",
    "source_url": "<source URL>",
    "coverage_status": "observed",
    "method_version": "<method version>",
    "dataset_version": "v1",
    "sample": false
  }
}
```

All 12 properties are always present. Nullable means the value is `null`, never a missing key.

| Rule | Why |
|---|---|
| `layer_id`, `hazard_type`, `observation_date`, `source_name`, `source_url`, `method_version`, `dataset_version` and `sample` equal their layer and manifest values | Every zone is traceable on its own (AGENTS.md rule 5) |
| `classification` is the source's category, verbatim, or `null` | PRD 8.1 rule 6. Never Low, Medium or High without a documented method |
| `unit` is required when `measurement` is set, and must be `null` when it is not | A bare number cannot be read |
| `measurement` is finite | No NaN or infinity |
| `coverage_status` is `observed` or `not_observed` | See Section 4 |
| `not_observed` zones have `classification` and `measurement` both `null` | "No flooding mapped" must not carry a value that reads like a result |
| The geometry is valid, WGS84 and inside the layer's coverage (0.1 m tolerance) | Coverage and zones must agree |
| Zone IDs are unique across the dataset | `/api/v1/zones/{id}` |

Unit strings: `%`, `ha`, `m`, `mm/year`, and `NDVI` for the unitless index. Add new ones here when a module needs them.

## 4. `coverage_status` (PRD 8.2)

| Value | Meaning | Where it comes from |
|---|---|---|
| `observed` | The source detected or measured something here | Stored on the zone |
| `not_observed` | Inside the source's coverage, the source looked and detected nothing | Stored on the zone, **detection layers only** |
| `no_coverage` | Outside the source's coverage | Never stored. The API reports it per query (`coverage` status `none` or `partial`) |
| `not_assessed` | Layer unavailable, unbuilt or failed | Never stored. The layer is missing from the dataset |

**Detection layers** say whether something was seen: flood extent (CEMS, our Sentinel-1 map). A cell where the sensor looked and saw no water is `not_observed`.

**Measurement layers** report a value: ground velocity (EGMS), NDVI. A cell with no valid measurement is **not** `not_observed`. It is left out, so it falls outside the layer coverage and reads as `no_coverage`. Writing "no movement" or "no data" as `not_observed` would turn missing data into a result (AGENTS.md rule 1).

## 5. Two kinds of layers

| Kind | Geometry | Zone ID | Example |
|---|---|---|---|
| Source polygon layer | The source's own polygons, repaired and snapped | `{layer_id}-{hash of canonical geometry}` (PRD 7.5 step 6) | CEMS EMSR758 reference layers |
| Grid layer | One cell of the analysis grid | `{layer_id}-{cell_id}` | Our Sentinel-1 flood map, ground stability, land use |

Reference layers keep the source geometry, so CEMS polygons are shown as CEMS published them. Our own module layers use the grid, so all modules share the same cells and can be compared cell by cell.

## 6. The grid: `galati-utm35n-200m-v1`

Defined in `config/grid.yaml`. A published grid never changes: a new cell size, CRS or extent gets a new `grid_id`.

| Property | Value | Reason |
|---|---|---|
| CRS | `EPSG:32635` (UTM 35N) | All of Galați County lies in zone 35 (24°E to 30°E). Areas are measured in metres |
| Cell size | 200 m (4 ha) | A whole number of 10 m and 20 m Sentinel-1 and Sentinel-2 pixels. On a UTM grid aligned to 20 m, no pixel is split between two cells |
| Anchor | The CRS origin | A cell's lower-left corner is a multiple of 200 m, so cell IDs never depend on the extent |
| Cell ID | `E{x}_N{y}` | The lower-left corner in metres, for example `E560000_N5050000`. A point on an edge belongs to the cell above and to the right |
| Extent | `[511400, 5016200, 602000, 5122800]` m | 453 × 533 = 241,449 cells |
| Valid data rule | `min_valid_share: 0.5` | See Section 7 |

The extent is the box 27.15°E to 28.30°E and 45.30°N to 46.25°N, projected and rounded outward. It contains Pechea and Galați city. **It is an envelope around the county, not the county boundary.** Ingest clips to an official boundary once one is pinned.

**Size:** the Pechea pilot bounding box is about 15,100 cells. A grid layer that writes every cell is about 7.7 MB of GeoJSON and loads in about 3 s (measured on a laptop). A `GET /api/v1/zones` call for the whole pilot returns all of them, so the web app should limit cell layers by zoom level (LC-16, LC-17).

**In WGS84** a cell is a 5-point polygon: the four projected corners, rounded to 6 decimals (about 0.1 m), counter-clockwise. Neighbouring cells share their corners exactly. Use `Grid.cell_geometry(cell_id)`, never your own conversion, because the loader checks the polygon.

## 7. From a module result per cell to a zone

A module computes one result per cell for one observation (one date, one sensor, one method version). `landcheck.grid.grid_layer` applies the rule and returns the zones and the layer coverage:

1. **Pick the cells.** Take the cells that intersect the source's footprint (`Grid.cells_in_bbox_m`, then intersect with the footprint in `EPSG:32635`).
2. **Measure valid data.** For each cell, `valid_share` is the share of the cell covered by valid source data: inside the footprint, not masked (clouds, SCL classes, nodata).
3. **Drop thin cells.** Below `min_valid_share` (0.5), the cell is left out. It becomes `no_coverage`, never a result.
4. **Set the status.** Detection layers: `observed` if the hazard was detected in the valid part of the cell, otherwise `not_observed`. Measurement layers: `observed` with the value. A cell without a valid value is left out (step 3).
5. **Set the values.** Use the source category as `classification` and the cell value as `measurement` with its `unit`. `not_observed` has neither.
6. **Build the layer.** The zone ID is `{layer_id}-{cell_id}` and the geometry comes from `Grid.cell_geometry`. Layer coverage is the union of the zones' cells, so a click inside the coverage always finds a zone.
7. **Write.** `write_dataset` writes the files, `feature_count` and checksums. Set `grid_id` on the layer.

`CellResult` and `cell_zone` reject results that break the format: a stored `no_coverage` or `not_assessed`, a value on `not_observed`, a measurement without a unit, NaN, or `valid_share` outside 0 to 1.

### Proposed values per module

The module owners confirm these. Thresholds go in `config/thresholds.yaml`, and no Low, Medium or High is set from placeholder thresholds (AGENTS.md rule 3).

| Module | Kind | `measurement`, `unit` | Notes |
|---|---|---|---|
| Sentinel-1 flood extent | Detection | Flooded share of the cell's valid area, `%` | One layer per acquisition. `classification` stays `null` because there is no source category |
| Ground stability (EGMS Ortho) | Measurement | Median vertical velocity of the points in the cell, `mm/year` | Points are in `EPSG:3035`. Transform them to `EPSG:32635` before `Grid.cell_id`. Cells with fewer than `ground.min_points` points are left out. The format has one date: use the last acquisition date and state the period in `meaning` |
| Land use (summer NDVI) | Measurement | Mean summer NDVI of valid pixels, `NDVI` | One layer per year. A land-cover class would go in `classification`, verbatim from its source |

## 8. What the loader checks

`load_dataset` fails, and the API answers `503 DATASET_UNAVAILABLE`, when:

- a file is missing, is not JSON, or does not match its SHA-256 in the manifest;
- a manifest field is missing, unknown or of the wrong type;
- layer IDs repeat, `coverage.geojson` does not have exactly one feature per layer, or `layers/` holds a file the manifest does not list;
- a layer file's feature count differs from `feature_count`;
- a zone breaks a rule in Section 3;
- a grid layer names an unknown grid, or a zone's ID is not `{layer_id}-{cell_id}` for a valid cell in the extent, or its geometry is not that cell's polygon.

The same rules run in CI through `tests/test_dataset.py` on synthetic data, and through `tests/test_api.py` on the bundled sample fixture.
