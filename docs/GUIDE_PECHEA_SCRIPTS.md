# Guide: from downloaded data to the LandCheck modules (Pechea)

This guide explains what we did after downloading the Pechea data (see `GHID_DESCARCARE_DATE_PECHEA.md`): how raw data became clean data, what each code file does, how to run it, and why each rule was chosen. It does not assume programming knowledge. Every file has a section with input, output and rules.

## 1. The big picture

The app receives a **parcel** (a plot drawn on the map) and answers three questions, one "module" for each:

| Question | Module | Data used |
|---|---|---|
| Was the parcel under water? | `flood_history` | CEMS flood extent (13–17 Sep 2024), plus rain, terrain and permanent water as context |
| How did vegetation change over the years? | `land_use` | Summer NDVI 2018–2025 |
| Is the ground moving? | `ground_stability` | EGMS radar points 2020–2025 |

The flow has two big steps:

```
raw data (data/, outside git)
   │   "ingest" scripts: verify, clean, cut the zone, write small files
   ▼
clean dataset (datasets/pilot-pechea/, in git)
   │   modules: read the dataset and answer for one parcel
   ▼
result in the shared format (ModuleResult): level, value, confidence, text, sources
```

### Rules all the code follows (PRD section 8)

1. **No data means "Unknown", never "low risk".** If we have nothing about the parcel, we say "No coverage".
2. **No invented risk classes.** High, Medium or Low appear only when a documented method supports them. Otherwise we show the measurement.
3. **Coordinates:** stored in WGS84 (lon, lat). Measuring (areas, distances) happens in metres, in UTM (EPSG:32635 for Pechea).
4. **Raw data stays out of git.** Only small processed data goes in.
5. **Output is deterministic:** the same input gives the same files, byte for byte.
6. **A wrong checksum stops everything.** A script never continues with unverified data.

## 2. What we did, step by step

### Step 0. Setup
- New branch from `dev`: `feature/cems-ingest`. Project rule: one branch per piece of work, PR into `dev`, `dev` and `main` are protected.
- The Python environment (`.venv`) was recreated at the project root:
  ```
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -e ".[dev,ingest,landuse]"
  ```
- In `pyproject.toml`: new extra `ingest = ["geopandas"]`, and `landuse` now also includes `rasterio`.

### Step 1. CEMS floods → `datasets/pilot-pechea/v1` (`ingest/cems.py`)
The three CEMS archives were verified (SHA-256 checksums pinned in the PRD), read, cleaned and written in the format the API requires. Result: 108, 131 and 237 polygons, with 1, 2 and 63 geometries repaired. The areas (1078.6, 866.7 and 427.4 ha) match the PRD.

### Step 2. The flood module (`modules/flood.py`)
The parcel is compared with the three layers. There are three possible results: overlap (High), inside the image but no polygon (Unknown, "does not mean it is safe") or outside the image (No coverage).

### Step 3. Land use (`modules/landuse.py`)
Reads the summer NDVI for each year from `pechea_ndvi_vara_2018_2025.tif`. It does not classify the land, because one value per summer is not enough for that.

### Step 4. Ground movement: data and scripts
- First we tried the area average copied by hand from the EGMS Explorer. It says nothing about a specific parcel.
- The solution: the official download of EGMS "tiles" (the Download button in the Explorer). We downloaded 4 tiles of 100 km (two for each component, vertical and east-west), about 450 MB in total.
- `ingest/egms.py` cuts only the pilot zone out of them (14,608 points) and writes a small CSV.
- `modules/ground.py` looks up the points around the parcel and gives the median velocity.
- **Check:** the mean of the nearest 508 points in the downloaded files is −0.702 mm/yr, against −0.698 in the Explorer (difference 0.004). East-west: 0.043 against 0.031. The data are consistent.

### Step 5. Flood context (`modules/flood_context.py`)
Rain, terrain and permanent water added next to the flood result. They never change the level.

### Step 6. Tests and commits
One set of tests per file. At the end, 78 tests pass. Local commits on `feature/cems-ingest`:

| Commit | Content |
|---|---|
| `d2bd40c` | CEMS ingest and the `pilot-pechea/v1` dataset |
| `3fa09d7` | `flood_history` |
| `4275b03` | `land_use` |
| `e755f1e` | EGMS ingest and `ground_stability` |
| `e9ceaed` | flood context (rain, terrain, JRC) |

## 3. What each file does

### 3.1 `landcheck/ingest/cems.py`

**Role:** turns the three CEMS archives into the dataset the API reads.

**Input:** `data/cems/EMSR758_AOI03_*.zip` (3 files).
**Output:** `datasets/pilot-pechea/v1/` with `manifest.json`, `coverage.geojson` and `layers/<layer_id>.geojson` (3 layers), plus the report `datasets/pilot-pechea/v1.ingest.json`.

**Steps, in order:**
1. Checks the size and SHA-256 checksum of each archive against the values in the PRD (7.3). If one is wrong, it stops before writing anything.
2. Unzips and reads three layers: `observedEventA` (the flooded polygons), `areaOfInterestA` (the requested area) and `imageFootprintA` (what the satellite saw).
3. Repairs invalid polygons (`make_valid`), keeps only surfaces, and records how many were repaired and how the area changed.
4. Computes the area in EPSG:32635.
5. The coverage of each layer = requested area ∩ area seen by the satellite.
6. Snaps coordinates to about 0.1 m, orients rings per RFC 7946, and gives each polygon an **ID computed from its shape** (`<layer_id>-<12-character hash>`). The same shape always gets the same ID.
7. Writes the files, then the hash of each file into the report.

**Rules:**
- Refuses to write over an existing folder. Dataset versions are immutable; a change means a new version.
- The polygon count is checked against the PRD (108, 131, 237).
- The report lives outside the `v1` folder, because the API rejects extra files in a dataset.

**Run:**
```
python -m landcheck.ingest.cems --raw data/cems --out datasets/pilot-pechea/v1
```

### 3.2 `landcheck/modules/flood.py`

**Role:** answers "was the parcel mapped as flooded?". It returns two results: `flood_history` and `flood_susceptibility` (the latter only says "Not assessed", because the model is outside the MVP).

**Input:** a parcel (`Parcel`). **Reads:** `datasets/pilot-pechea/v1` (or the folder in the `LANDCHECK_DATASET_DIR` variable).

**How it decides, for each layer:**
- Measures in metres, in the parcel's UTM: how much of the parcel the satellite saw and how much was mapped as flooded.
- Overlap ≥ 1 m² → `observed`. Covered but no overlap → `not_observed`. Outside the image → `no_coverage`.

**Final result:**
- At least one layer with flooding: level **High**, value = the largest share of the parcel, confidence High if the images cover the parcel completely, otherwise Medium. The text gives the date, the sensor, and says it is one image, not the flood peak.
- Parcel covered but no polygon: **Unknown**, with the text "this does not mean the land is safe".
- No image covers the parcel, or the dataset is missing: **Unknown**, "No coverage".

### 3.3 `landcheck/modules/flood_context.py`

**Role:** adds facts next to the flood result, without changing the level. Any missing part, or a parcel outside the data, is skipped without an error.

**Data (in `datasets/pilot-pechea/context/`):**

| Part | File | What it says |
|---|---|---|
| Rain | `ploaie_grid_pechea_sep2024.csv` | 5-day total up to the image date, the rainiest day, from the grid cell (0.01°) nearest the parcel |
| Terrain | `pechea_dem_relief.tif` | Elevation, slope, and how much of the land within 2 km is lower than the parcel |
| Permanent water | `pechea_jrc_occurrence_v1_5_eocube.tif` | Whether the parcel's pixels have water ≥ 50% of the time |

**How it appears in the result:** everything goes into `details["context"]`. Only rain and permanent water add a sentence to the text, and only when the parcel was mapped as flooded. Real example: "Rain in the 5 days up to 2024-09-14: 81.9 mm (most on 2024-09-14, 64.4 mm)."

**Note:** DEM and JRC are at 30 m, so they are approximate for small parcels. The 50% threshold comes from `config/thresholds.yaml` (a provisional value).

### 3.4 `landcheck/modules/landuse.py`

**Role:** shows how the parcel's summer vegetation varied between 2018 and 2025.

**Input:** the parcel. **Reads:** `data/landuse/pechea_ndvi_vara_2018_2025.tif` (or `LANDCHECK_NDVI_PATH`). The file is not in git because it is large (53 MB).

**How it works:**
- For each year it takes the median NDVI of the pixels (20 m) inside the parcel. Empty pixels stay empty, with no filling.
- Parcel smaller than a pixel: it takes the pixel the parcel touches.
- Parcel only partly in the area: it says what percentage is inside.

**Result:** level always **Unknown**. The text gives the range ("between 0.17 and 0.76, 2018–2025") and states that only summer is measured, so it does not show how the land was used. If NDVI is below 0.2 in every year, it adds "sparse vegetation".

**Why it does not classify:** telling a field from a forest needs the growth cycle across the whole year. A weak year (2024, for example) can just be drought. Classification can be added once we have spring and autumn NDVI.

### 3.5 `landcheck/ingest/egms.py`

**Role:** cuts only the pilot zone out of the large EGMS tiles and makes them usable.

**Input:** the `data/egms/EGMS_L3_*` folders (vertical `U` and east-west `E`, each with a CSV). Each CSV row = one radar point, with coordinates in EPSG:3035, mean velocity in mm/yr and the time series.
**Output:** `datasets/pilot-pechea/ground/egms_ortho_pechea_2020_2025.csv` (14,608 points, without the time series) and the `.ingest.json` report.

**Steps:**
1. Finds the tiles and requires both components for each tile. If one is missing, it stops.
2. The zone = CEMS coverage + 5 km, as a rectangle in EPSG:3035.
3. Reads each CSV row by row (the files are ~135 MB) and keeps only the points inside the zone.
4. Joins vertical and east-west by point ID and converts coordinates to lat/lon.
5. Writes the CSV sorted by ID, so it is deterministic.
6. In the report: the checksums of the 4 CSVs, the point count and the **check against your Explorer averages** (the mean of the nearest K points against the published average).

**Run:**
```
python -m landcheck.ingest.egms --raw data/egms \
  --coverage datasets/pilot-pechea/v1/coverage.geojson \
  --out datasets/pilot-pechea/ground/egms_ortho_pechea_2020_2025.csv \
  --average data/egms/egms_pechea_medie_508_vertical.txt \
  --average data/egms/egms_pechea_east_west.txt
```

### 3.6 `landcheck/modules/ground.py`

**Role:** for a parcel, says how the ground is moving (mm/yr, negative = sinking).

**How it works:**
1. Reads the small points CSV (once, then keeps it in memory).
2. Takes the points inside the parcel plus the buffer (500 m), in EPSG:3035.
3. No point → **No coverage** (never "stable"). Radar points exist only on buildings, roads and bare ground; fields rarely have any.
4. Otherwise it computes the vertical median, the interquartile range (how much the points disagree), the number of points, the east-west median and the acceleration.

**Confidence:**
- High: at least 10 points and quartiles less than 1 mm/yr apart.
- Medium: at least 3 points (the threshold in `thresholds.yaml`) and a difference below 2 mm/yr.
- Low: otherwise. If neighbours disagree, the text adds "treat with caution".

**The level stays Unknown.** The thresholds in `thresholds.yaml` (−2 and −5 mm/yr) are provisional and have no documented method. The measured value is shown. If the team adopts the thresholds, this changes in one place.

### 3.7 Tests (`tests/`)

| File | What it checks |
|---|---|
| `test_ingest_cems.py` | Invalid polygon repaired; stable ID; wrong checksum stops; the dataset loads in the API; two runs give identical files; refuses to overwrite; nothing written if an archive is tampered with |
| `test_flood.py` | Parcel in a flooded zone = High; partly in the zone = percentage; covered with no polygon = Unknown; outside the image = No coverage; missing dataset; one test on the real data |
| `test_flood_context.py` | Rain (sum, peak day, nearest cell), terrain (slope, position), JRC, missing files, context in the result |
| `test_landuse.py` | NDVI range, sparse vegetation, parcel under one pixel, partly outside, outside, missing file, test on the real raster |
| `test_ingest_egms.py` | Cutting to the zone, joining vertical + east-west, the averages check, incomplete tile, refusal to overwrite |
| `test_ground.py` | High confidence, disagreeing neighbours, no points = No coverage, missing file, distant parcel |

Tests that need large files outside git (the CEMS archives, the NDVI raster) **skip themselves** when those files are absent. The rest use small data created on the fly. Run: `pytest` (78 tests).

### 3.8 Where everything lives

```
data/                      raw data, outside git (CEMS, EGMS, NDVI, s1, s2, etc.)
datasets/pilot-pechea/
├── v1/                    CEMS floods (read by the API): manifest, coverage, 3 layers
├── v1.ingest.json         report of the CEMS ingest (checksums, repairs)
├── context/               rain, terrain, JRC (+ README with the sources)
└── ground/                EGMS points in the zone (+ the ingest report)
landcheck/ingest/          scripts that build the dataset (cems.py, egms.py)
landcheck/modules/         modules that answer for one parcel
tests/                     the tests
```

## 4. Decisions and open points

| Topic | What we chose | Why |
|---|---|---|
| Level for `land_use` and `ground_stability` | Unknown | No documented method (PRD 8.1) |
| Level for floods | High only when overlapping a mapped polygon | It is an observed fact; no polygon does not mean low risk |
| Context (rain, terrain, JRC) | Facts only, never changes the level | Avoids an artificial combined score |
| JRC | Included, although CEMS already separates permanent water | Cheap to add and useful as a warning |
| Ingest report | Separate file, outside the dataset | The API rejects extra files |
| Data in git | The clean dataset and the small context (~6 MB). Rasters with `git add -f` | `.gitignore` ignores `*.tif` |
| Terms of use | The data are treated as open | The PRD asks for confirmation (D-03), to be mentioned in the PR |

**To align with the partner:** the manifest in PRD 7.4 has fields the API's strict loader does not accept. Also the source attribution, and the EGMS and CEMS terms for commercial reuse.

## 5. What is not done

- Real land-use classification (needs NDVI across the whole year).
- Risk classes for ground movement (needs a documented method).
- ANAR flood-hazard maps (no machine-readable source).
- The Sentinel-2 offset correction in `core/s2.py` (only needed if S2 from EOCube is used).
- The rain context covers September 2024 only (other events need other data).

## 6. Full run from scratch

```
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,ingest,landuse]"
python -m landcheck.ingest.cems --raw data/cems --out datasets/pilot-pechea/v1
python -m landcheck.ingest.egms --raw data/egms --coverage datasets/pilot-pechea/v1/coverage.geojson \
  --out datasets/pilot-pechea/ground/egms_ortho_pechea_2020_2025.csv
pytest
```

If the folder `datasets/pilot-pechea/v1` or the EGMS file already exists, the scripts refuse to write over them. Delete them on purpose, or use a new name.
