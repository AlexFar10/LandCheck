# AGENTS.md

Instructions for every coding agent and contributor working in this repository. `CLAUDE.md` and `CODEX.md` point here, so add shared rules to this file only.

## Project

Land Check is a map-first geographic hazard screening tool for insurance agencies. An analyst selects a mapped area and sees documented hazards with their source, date, meaning and limitations.

- **Delivery target:** ROSPIN demo on December 11, 2026. Release freeze on December 10.
- **MVP:** one pilot zone, at least one real flood layer, a FastAPI backend and a React map.
- **Pilot zone:** Pechea, Galați County (Copernicus EMS EMSR758, AOI03), confirmed in PRD decision D-01.

## Read first

| Need | Source |
|---|---|
| Requirements, API contract, backlog, decisions | [`docs/PRD.md`](docs/PRD.md) |
| Delivery constraints and team split (authoritative if sources conflict) | [`docs/Land_Check_PRD_Addendum_2_Week_MVP.md`](docs/Land_Check_PRD_Addendum_2_Week_MVP.md) |
| Scientific method and data background | [`docs/deep-research-report.md`](docs/deep-research-report.md) |
| Python module contract | [`README.md`](README.md) |
| Layer format, cell grid and coverage rules for every dataset | [`docs/LAYER_FORMAT.md`](docs/LAYER_FORMAT.md) |
| Pull, set up and run the project | [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) |
| Coolify deployment, rollback and CI | [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) |
| Task for the agent on the VPS | [`docs/VPS_AGENT_TASK.md`](docs/VPS_AGENT_TASK.md) |

The research report's Lower Olt product, five-week plan and larger architecture are superseded. Use it for scientific method, not scope.

## Current state

- `landcheck/` (repo root) is the satellite-data package. The API in `landcheck/api/` does not call the modules yet.
- Built: `landcheck/core/` and its tests.
- Stubs: `landcheck/modules/flood.py`, `ground.py`, `landuse.py`.
- Skeleton: FastAPI app in `landcheck/api/` with the PRD Section 12 endpoints, and React + MapLibre map in `web/`. The API serves a labelled sample fixture from `landcheck/api/fixtures/sample/` until the pilot dataset exists.
- Not started: pilot dataset, working deployment.
- CI: `.github/workflows/ci.yml` runs on `dev` and `main`. The `ci` stage in `Dockerfile` makes lint and test results visible in Coolify build logs, so keep its `COPY --from=ci` dependency.
- Before using Sentinel-2 output, read defects D1 and D3 in PRD Section 6.2. `s2.offset_for_item` currently returns the wrong offset for many EOCube items.

## Setup and commands

Use Linux or WSL. These commands were verified on Ubuntu 24.04 with Python 3.12:

```bash
python3 -m venv --copies .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m landcheck.pipeline   # all modules return Unknown until built
```

If one checkout is shared between Windows and WSL, WSL Git can report every file as modified because of CRLF line endings. Run `git config core.autocrlf true` in that checkout, or keep a separate clone inside WSL. Do not commit line-ending-only changes.

API and web app (see [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)). The `dev` extra above already installs the API dependencies, and `pytest` runs the API tests:

```bash
# API on http://127.0.0.1:3000, OpenAPI docs at /docs
uvicorn landcheck.api.main:app --reload --host 127.0.0.1 --port 3000
python -m landcheck.api        # production style: 0.0.0.0:${PORT:-3000}

# Web app on http://127.0.0.1:5173, proxies /api and /health to the API on PORT
cd web
npm ci
npm run dev -- --host 127.0.0.1
npm run lint && npm test && npm run build
```

`docker build -t landcheck:local .` builds the interim image and runs lint and tests. On Windows, use the Docker engine inside WSL.

## Repository map

```text
config/thresholds.yaml   Versioned thresholds, currently unvalidated placeholders
config/grid.yaml         Analysis grid for module layers (docs/LAYER_FORMAT.md)
docs/                    PRD, addendum and research
landcheck/core/          Shared parcel, Sentinel-2, output and config code
landcheck/modules/       Hazard modules
landcheck/pipeline.py    Runs all modules on one parcel
tests/                   Pytest suite for landcheck/
landcheck/api/           FastAPI app (PRD Section 12) and its sample fixture
landcheck/grid.py        Grid cells and the per-cell zone rule
landcheck/dataset_files.py  Writes dataset folders with counts and checksums
web/                     React + Vite + MapLibre map
index.html               Current "under construction" page
```

Proposed additions are `landcheck/ingest/` and `datasets/`. Do not put versioned pilot data under `data/`, because `.gitignore` excludes it.

## Product and science rules

These rules are mandatory.

1. **No data is never low risk.** Keep `observed`, `not_observed`, `no_coverage` and `not_assessed` distinct. Never describe an empty result as safe.
2. **No invented facts.** Do not invent data availability, values, precision, model accuracy, legal suitability or EOCube capabilities. Flag unknowns for confirmation.
3. **Risk classes need a documented method.** Otherwise show the source measurement or official category. Do not surface values derived from placeholder thresholds as Low, Medium or High.
4. **No combined hazard score** in the MVP.
5. **Every displayed value must be traceable** to source, date, dataset version and method version. Do not hard-code values in the UI.
6. **Sample data must be labelled.** Illustrative numbers must never appear as real results.
7. **The app is a screening tool.** Do not claim engineering, legal, underwriting, premium or actuarial conclusions.
8. **The demo uses precomputed data.** A user click must not trigger satellite processing.
9. **The LLM never computes risk.** It only explains module results. It does not set or change levels, values or dates.

## Geospatial rules

- Store coordinates in WGS84 as `(lon, lat)`. Measure in the correct UTM zone. Romania spans zones 34 and 35, so never hard-code a zone in shared code.
- Calculate areas in a projected CRS, never in degrees.
- Record scene or dataset IDs and dates for every result.
- Apply reflectance scaling and offsets per source, item and band.
- Mask Sentinel-2 SCL classes 0, 1, 3, 8, 9, 10 and 11 before computing indices. Class 11 still needs adding to the code.
- Fail loudly. No `fail_on_error=False`, silent fills or `ffill`.
- Resampling does not add information. Compute SWIR-based products at 20 m.
- Never name a field just `ndwi`. Use `ndwi_water_mcfeeters` or `ndwi_vegetation_gao`.
- Thresholds belong in `config/thresholds.yaml`. Bump its version when values change.
- For any ML, hold out whole basins, regions or years. Never split pixels randomly.
- Check dataset licenses before use. EOCube `uvt-*` layers are CC-BY-NC-ND and must not be used without permission.

## Python module contract

```python
RISKS = ("ground_stability",)
def run(parcel: Parcel) -> list[ModuleResult]: ...
```

Use `no_coverage(...)` when a module has no data. Changes to `landcheck/core/` require review from its owner.

## API contract

Keep the backend aligned with PRD Section 12:

```text
GET /health
GET /api/v1/layers
GET /api/v1/zones?bbox=west,south,east,north
GET /api/v1/zones/{id}
```

Zone fields: `id`, `geometry`, `hazard_type`, `classification`, `measurement`, `unit`, `observation_date`, `source_name`, `source_url`, `coverage_status`, `method_version`. `classification`, `measurement` and `unit` are nullable. Render null as "Not available," never as `0`.

Every layer, from any module, uses the shared format in [`docs/LAYER_FORMAT.md`](docs/LAYER_FORMAT.md): the manifest fields and checksums, the zone rules, `coverage_status` (only `observed` and `not_observed` are stored), and the 200 m grid in `config/grid.yaml` for module layers. `load_dataset` enforces it.

If the contract must change, update the PRD, backend and frontend in the same PR.

## Git workflow

- Work from a GitHub issue, on one branch per issue, created from the latest `dev`: `feature/24-risk-map`, `fix/31-empty-state`.
- Open PRs into `dev`. Promote tested work from `dev` to `main` through a reviewed PR.
- **Never push directly to `main`. Every change on `main` auto-deploys.**
- Do not merge to `main` until Coolify uses the Dockerfile build pack (`docs/DEPLOYMENT.md` Step 5).
- PRs must pass the `CI passed` check. CI tests must not need network access or real credentials.
- One person writes and another reviews. No self-approval.
- Rebase on the latest `dev` before merging. Keep PRs reviewable within a day.
- PRs include the issue reference, tests run, screenshots for UI changes and the reviewer.
- Agents commit, push or open PRs only when asked.
- Stay in scope of the issue. List other problems in your final message instead of fixing them.
- Every change comes with tests.
- Never edit code on the VPS directly. Changes reach the server only through git.

**Review pairs:** Ceca reviews Raul's requirements and issues. Alexandra and Emilia review each other. Stefana and Alexandru review each other. Bianca and available teammates cross-review infrastructure and workflow changes.

## Security

- Secrets live only in `.env`, never in code, tests, commits or logs. `.env.example` lists every variable name with safe example values.
- **This repository is public.** Never commit secrets, `.env` files, server IPs, internal URLs, open-port details or infrastructure notes.
- Upstream credentials stay server-side and never reach the frontend bundle.
- Validate API inputs. Do not accept user-supplied file paths, asset URLs or GDAL paths.
- Return safe API errors. Log internal exception details server-side only.
- On the shared server, do not run agents in approval-bypass modes such as `codex --yolo`. Do not change Coolify, firewall, Docker or system settings unless a person explicitly asks for that change.

## Before finishing work

1. Run `pytest` and the backend and frontend checks for the parts you changed, and report the actual results.
2. For UI changes, run the app and check the affected states.
3. For data changes, compare values with the source and update the manifest.
4. Update the PRD or this file if behavior, commands or decisions changed.
5. Report what you verified, what you could not verify and any remaining risk.
