# Land Check

Select an area on a map and get a risk report on floods, ground stability and land-use history
from satellite data. Requirements, API contract and decisions: [docs/PRD.md](docs/PRD.md).
Pilot zone: Pechea, Galați County (PRD decision D-01).

The repository has two parts:

- **Satellite-data core** (`landcheck/`, `config/`, `tests/`): the shared core is implemented and
  tested. Each risk module is a stub that sets out its interface, data sources and steps, for its
  owner to build.
- **Platform skeleton** (`landcheck/api/`, `web/`): a FastAPI app with the PRD Section 12
  endpoints and a React + MapLibre map centred on the pilot. The API serves a clearly labelled
  **sample fixture** until the pilot dataset exists.

## Layout

| Path | What |
|---|---|
| `landcheck/` | Satellite-data package: core and hazard modules (see below) |
| `config/` | Versioned thresholds (`thresholds.yaml`, placeholders for now) |
| `tests/` | Pytest suite for `landcheck/` |
| `landcheck/api/` | FastAPI app: `GET /health`, `/api/v1/layers`, `/api/v1/zones`, `/api/v1/zones/{id}` |
| `web/` | React + Vite + MapLibre map |
| `contracts/` | Shared module result JSON schema and mock results, one per risk |
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

## Platform (API and web app)

Full instructions, including the shared-server ports, are in
[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md). In short (Python 3.10+, Node.js 24):

```bash
pip install -e ".[dev]"                                   # includes the api extra
uvicorn landcheck.api.main:app --reload --host 127.0.0.1 --port 3000
cd web && npm ci && npm run dev -- --host 127.0.0.1       # http://127.0.0.1:5173
```

The web dev server proxies `/api` and `/health` to the API on `PORT`. API docs are at
http://127.0.0.1:3000/docs.

### Checks

```bash
pytest
cd web && npm run lint && npm test && npm run build
```

## Configuration

All configuration is through environment variables (or the repo-root `.env`), as listed in PRD
Section 11.5. See [.env.example](.env.example). Data-provider credentials stay server-side. In a
container, `python -m landcheck.api` binds `0.0.0.0:${PORT:-3000}`.
