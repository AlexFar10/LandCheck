# ROSPIN / Land Check: PRD addendum and team organization

**Updated:** November 22, 2026  
**Deadline:** December 11, 2026  
**Team:** 7 people  
**Time available:** About two effective working weeks; scope must fit the deadline.

## 1. Product direction and MVP boundary

Land Check is a **map-first geographic hazard screening tool for insurance agencies**. An analyst opens a map, selects an area or a marked zone, and sees which documented hazards may be relevant before inspecting a property or portfolio further.

- **Start with one small pilot zone in Romania**, selected by November 23 based on available evidence and demonstrable data. Do not build nationwide coverage now. Design the data model so new regions can be added later.
- **Core demo:** interactive map with clearly marked polygons/points, a simple hazard legend, layer toggles, and a click-to-open evidence panel containing hazard type, observation or map date, source, and data-coverage status.
- **First mandatory hazard:** flood history and/or official flood-hazard zones, using a verified source for the chosen pilot. Prefer preprocessed layers that can load reliably at demo time.
- **Conditional additions:** ground movement (EGMS, where measurements exist) and land-use history (Sentinel-2 / land-cover products), only if the core map works. They can be evidence/context layers without an artificial combined score.
- **Optional if time remains:** draw a parcel, summarize overlapping hazards, generate a downloadable screening report, and support additional zones.
- **Out of scope for December 11:** national coverage, insurance premiums, actuarial loss predictions, legal buildability certification, real-time satellite ingestion, and a complex ML model without credible training data and validation.

Risk classes (for example, low/moderate/high) may be shown **only where a documented classification method supports them**. Otherwise show the underlying measurement or official category; distinguish **unknown/no coverage** from **low risk**. A hazard screening result is not an engineering survey or underwriting decision.

## 2. Team split: seven people, five workstreams

| Owner | Task | Deliverable / handoff |
|---|---|---|
| **Raul** | Requirements and GitHub issues | MVP scope, user stories, acceptance criteria, milestone grouping, priorities; resolve the single pilot zone with the team. |
| **Ceca** | Environment, `AGENTS.md` / `CLAUDE.md`, and minimum backend + frontend skeleton | Running FastAPI and React projects, shared run instructions, Docker/dev setup if feasible, `/health`, a sample API response; review Raul's requirements and issues. |
| **Bianca** | GitHub branches and repository workflow | Create initial branches; configure `main` and `dev` protections, PR template and issue conventions; help unblock branch/merge conflicts. |
| **Alexandra + Emilia** | Simplest possible clickable demo | Figma wireframe and React/TypeScript map view with one selectable layer, clickable zone and risk/evidence side panel; first use fixture JSON, then switch to real API. |
| **Stefana + Alexandru** | Satellite / geospatial data and integration | One sets up the EOCube project and invites the whole team; the other verifies access for everyone. Together obtain, process and display one real pilot-zone dataset, expose it through the backend and confirm the rendered values match the source. |

Each pair works in parallel and reviews the partner's PRs. **Integration is shared:** the map pair owns the UI-to-API connection, the data pair owns geospatial correctness, and Ceca supports the backend contract and developer environment. Nobody waits for one central person to approve every change.

## 3. Fixed milestones and integration gates

| Date | Goal / acceptance gate |
|---|---|
| **Nov 23** | Requirements and prioritized GitHub issues ready; pilot zone selected; repository workflow and environment documented; `AGENTS.md` in place. |
| **Nov 25** | Bare-minimum FastAPI + React skeleton runs; EOCube project and team access verified; clickable map demo with fixture data; first satellite/official dataset retrieved or access blocker documented. |
| **Nov 28** | One **real** georeferenced hazard layer for the pilot can be displayed on the map; zone-click panel shows source and date. |
| **Dec 2** | Frontend reads real backend API data; layer legend, loading/empty/error states and `unknown/no coverage` behavior implemented. Add a second dataset only if reliable. |
| **Dec 5** | End-to-end demo from opening map to selecting a zone and reading evidence; spatial data validated with known source samples. |
| **Dec 8** | Testing, attribution, limitations, short demo walkthrough; optional parcel summary/report only if the core path is stable. |
| **Dec 10** | Release freeze: `main` stable, final dataset cached, deployment and fallback demo tested. |
| **Dec 11** | ROSPIN demonstration. No major feature merges on demo day. |

The November 23 and 25 dates are the original agreed milestones; subsequent dates are **proposed integration gates** and can be moved without weakening the December 11 freeze.

## 4. Git workflow (mentor guidance)

- Write GitHub issues as **user stories** with acceptance criteria; group them in milestones. Track bugs as issues too.
- Use **one branch per issue** (for example, `feature/24-risk-map`), with a PR template that includes issue reference, tests, screenshots for UI changes, and reviewer.
- Protect `main` and `dev`. Feature branches merge through reviewed PRs into `dev`; promote tested, demo-ready changes from `dev` to `main`.
- **One person writes, another reviews.** Rebase on the latest `dev` before merging. No self-approval.
- Ceca reviews Raul's requirements/issues; Alexandra and Emilia review each other's changes; Stefana and Alexandru review each other's changes. Bianca and the remaining available teammates cross-review infrastructure/workflow PRs. Avoid a single-reviewer bottleneck.
- Keep PRs small enough to review within a day. Avoid merging untested data changes immediately before the demo.

## 5. Agreed stack and technical handoff

| Layer | Tool | Immediate requirement |
|---|---|---|
| Backend | **Python + FastAPI** | `GET /health`, `GET /api/v1/layers`, `GET /api/v1/zones?bbox=...`, `GET /api/v1/zones/{id}`; return valid GeoJSON/JSON. |
| Frontend | **TypeScript + React** | Map, layer toggles, clickable markers/polygons, legend, source/evidence panel. |
| Frontend design | **Figma** | One clear desktop layout; prioritize a functional map over polish. |
| Satellite data platform | **EOCube** | Confirm access, supported exports/APIs and processing permissions on Nov 23–25; store processed results for deterministic demo use. |
| Geospatial storage | **GeoJSON files initially; PostGIS if needed** | One pilot zone, reproducible data version, stable feature IDs and source metadata. Avoid premature database complexity. |
| Mapping library | **MapLibre GL JS** (proposed) | Render the georeferenced results in React; select/deselect layers and features. |

**Minimal API object:** `id`, `geometry`, `hazard_type`, `classification` (nullable), `measurement` (nullable), `unit` (nullable), `observation_date`, `source_name`, `source_url`, `coverage_status`, `method_version`. Real values must be traceable to source data, not hard-coded UI decorations.

Prefer **offline/precomputed data ingestion** plus small REST responses for the demo. The app should not require a fresh satellite-processing request whenever someone clicks a polygon. If live EOCube access is unavailable, the data pair can export verified geospatial results for the pilot and serve them locally; document that fallback transparently.

## 6. Definition of done for December 11

A successful MVP means that an insurance analyst can open the deployed (or locally demoed) React app, identify the pilot zone, turn on at least one **real** hazard layer, click a mapped feature, and see a readable explanation with source, date, meaning and limitations. The FastAPI service and UI must agree on the returned values; an empty or unsupported area must not be called safe. There is a reproducible startup guide, a stable `main` branch, and a prerecorded/screenshotted fallback for a network outage.

**Not a blocker:** missing ML model, PDF export, automated nationwide ingestion, full multi-hazard score, or polished account management.

## 7. Instruction to the PRD-generating agent

Use this addendum as the **current authoritative delivery constraint** alongside the original Land Check concept and ROSPIN research dossier. The project remains **Land Check for insurance hazard screening**, not an Olt River drought-monitoring dashboard. Write the PRD for **seven named contributors and a December 11, 2026 demo**, not a five-week project.

Preserve the five workstreams, Nov 23/25 milestones, mentor Git workflow, and agreed FastAPI/React/Figma/EOCube stack. Separate must-have, conditional, and out-of-scope features. Provide small issue-sized user stories with concrete acceptance criteria, a single pilot-zone selection decision, sample GeoJSON/API contract, minimum UI screens, data-source provenance, scientific limitations, review ownership, integration gates and a short demo script. Do not invent data availability, scientific precision, model accuracy, legal suitability, or EOCube capabilities. Flag anything needing confirmation rather than treating it as implemented.
