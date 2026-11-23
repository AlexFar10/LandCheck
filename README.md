# Land Check

Select an area on a map and get a risk report on floods, ground stability and land-use history
from satellite data. Requirements, API contract and decisions: [docs/PRD.md](docs/PRD.md).
Pilot zone: Pechea, Galați County (PRD decision D-01).

The repository has two parts:

- **Satellite-data core** (`landcheck/`, `config/`, `tests/`): the shared core is implemented and
  tested. Each risk module is a stub that sets out its interface, data sources and steps, for its
  owner to build.
- **Platform skeleton** (`backend/`, `frontend/`, `contracts/`): the backend returns mock results
  in the shared result format ([contracts/result.schema.json](contracts/result.schema.json)). It
  will call the `landcheck/` package once modules are built.

## Layout

| Path | What |
|---|---|
| `landcheck/` | Satellite-data package: core and hazard modules (see below) |
| `config/` | Versioned thresholds (`thresholds.yaml`, placeholders for now) |
| `tests/` | Pytest suite for `landcheck/` |
| `backend/` | FastAPI app (Python 3.12, uv). `GET /health`, `POST /analyze` |
| `frontend/` | React + Vite + Leaflet map |
| `contracts/` | Shared result JSON schema and mock results, one per risk |
| `docs/` | PRD, addendum, research and setup guides |

## Satellite-data core

```
landcheck/
├── config/thresholds.yaml      # all thresholds, versioned (placeholders for now)
├── landcheck/
│   ├── core/                   # OWNER: ______  (everyone uses it, one person maintains it)
│   │   ├── parcel.py           # polygon -> Parcel (UTM zone, buffer, bbox)
│   │   ├── s2.py               # Sentinel-2: search, load, offset fix, SCL mask, indices
│   │   ├── output.py           # ModuleResult: the shared result format
│   │   └── config.py           # reads thresholds.yaml
│   ├── modules/
│   │   ├── flood.py            # OWNER: ______  flood_history, flood_susceptibility
│   │   ├── ground.py           # OWNER: ______  ground_stability (EGMS)
│   │   └── landuse.py          # OWNER: ______  land_use (Sentinel-2 NDVI)
│   └── pipeline.py             # runs all modules on one parcel, in parallel
└── tests/test_core.py
```

### The contract

Each module exposes exactly this:

```python
RISKS = ("ground_stability",)                 # names of the results it returns
def run(parcel: Parcel) -> list[ModuleResult]: ...
```

`Parcel` gives you: `geom_wgs84`, `geom_utm`, `area_utm` (parcel + buffer), `area_wgs84`, `bbox_wgs84`, `epsg`.

`ModuleResult` has these fields: `risk, level (Low/Medium/High/Unknown), value, unit, confidence, summary, sources, date_range, method_version, details`.

### Rules everyone follows

1. **Coordinates:** store in WGS84 as (lon, lat), measure in the parcel's UTM zone. Never hard-code a zone: Romania has zones 34 and 35.
2. **Provenance:** every result lists the scene or dataset IDs and dates it used.
3. **No data means `Unknown`**, never `Low`. Use `no_coverage(...)`.
4. **Fail loudly:** no `fail_on_error=False`, no silent fills, no `ffill`.
5. **Thresholds go in `config/thresholds.yaml`**, not in code.
6. **Validation:** hold out whole basins, regions or years. Never split pixels randomly.
7. **Changes to `core/`** go through its owner (PR review).

### Run

```bash
pip install -e ".[dev]"
pytest                       # core tests
python -m landcheck.pipeline # demo parcel: all modules return "Unknown" until built
```

### Open questions

- Do EOCube's COGs carry the +1000 offset in `raster:bands`? `s2.offset_for_item` handles both cases. Confirm on one post-2022 item.
- Do EOCube's terms allow commercial use?
- Sentinel-1 GRD isn't on EOCube, so the flood module needs Copernicus Data Space.
- What cadastre access (ANCPI/eTerra) do we have for parcel input?

## Platform (backend and frontend)

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (installs Python 3.12 itself)
- Node.js 24 and npm

Optional: `cp .env.example .env` in the repo root and adjust. Defaults work for local development.

### Run locally

Backend, on http://localhost:8000 (API docs at http://localhost:8000/docs):

```bash
cd backend && uv sync && uv run uvicorn landcheck.main:app --reload
```

Frontend, on http://localhost:5173:

```bash
cd frontend && npm install && npm run dev
```

Draw a polygon with the map's polygon tool, then click **Analyze**.

### Checks (same as CI)

```bash
cd backend && uv run ruff check . && uv run ruff format --check . && uv run pytest
cd frontend && npm run lint && npm test && npm run build
```

## Configuration

All configuration is through environment variables (or the repo-root `.env`). See
[.env.example](.env.example). Data-provider credentials stay server-side. On a Linux server, run
the backend with `uv run uvicorn landcheck.main:app --host 0.0.0.0 --port 8000` and set
`VITE_API_URL` before `npm run build`.
