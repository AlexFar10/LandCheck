# API sample fixture

`sample/` is **invented sample data** for API and UI development. It is not a real hazard
dataset and must never be shown as a result.

- Every layer, feature and `/health` response from it carries `"sample": true`, and its
  `dataset_id` is `sample-fixture`.
- The geometry is a few rectangles near Pechea, Galați County, so the map has something to
  draw. The date `2000-01-01` is a placeholder.
- `classification`, `measurement` and `unit` are `null` on purpose, so the UI has to render
  "Not available".

The folder uses the shared layer format (`docs/LAYER_FORMAT.md`, PRD Section 7.4 (`manifest.json`, `coverage.geojson`,
`layers/<layer_id>.geojson`). The manifest holds the SHA-256 of `coverage.geojson` and of each
layer file, so after editing a fixture file update its checksum (`sha256sum <file>`). The API serves it when `LANDCHECK_DATASET_DIR` is unset. Once the
pilot dataset exists (LC-15), set `LANDCHECK_DATASET_DIR=datasets/pilot-pechea/v1`.
