# Land Check: Getting Started

Follow this guide to pull the project, run it and start working on an issue.

## 1. What runs today

| Part | Status |
|---|---|
| Python core and tests | Works |
| Hazard modules | Stubs that return `Unknown` |
| API (`landcheck/api/`) | Skeleton with the PRD Section 12 endpoints. Serves a labelled **sample fixture**, not real data |
| Web app (`web/`) | React + MapLibre skeleton centred on Pechea. Lists layers from the API |

## 2. Requirements

- Git
- Python 3.10 or newer (3.12 is recommended)
- Node.js 24 and npm, for the web app
- Linux, macOS or WSL on Windows

Docker is only needed to test the production container.

**On Windows, use WSL.** Clone the project inside your WSL home folder (`~/`), not under `/mnt/c`. It runs faster and avoids line-ending problems. Use the Docker engine inside WSL as well, not Docker on Windows.

## 3. First-time setup

```bash
git clone https://github.com/AlexFar10/LandCheck.git
cd LandCheck
git switch dev

python3 -m venv --copies .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

If `python3 -m venv` fails on Ubuntu, run `sudo apt install python3-venv` and try again.

## 4. Check that it works

```bash
pytest
python -m landcheck.pipeline
```

You should see **43 passed**: the core tests and the API tests. The pipeline prints four results with level `Unknown`, which is correct until the modules are built.

The `dev` extra includes the API dependencies (`api` extra), so one install covers both.

## 5. Credentials

You do not need credentials to run the tests. If your task needs data access:

```bash
cp .env.example .env
```

Fill in only the accounts you need. **Never commit `.env`**, and never paste passwords or tokens into issues, PRs or chats.

## 6. Daily workflow

Start each task from the latest `dev`:

```bash
git switch dev
git pull --ff-only
git switch -c feature/24-risk-map
. .venv/bin/activate
```

Use the GitHub issue number in the branch name. Use `feature/` for new work and `fix/` for bugs.

Before opening a PR:

```bash
pytest
git fetch origin
git rebase origin/dev
git push -u origin HEAD
```

Then open a PR **into `dev`** with the issue number, tests you ran, screenshots for UI changes and your reviewer. Someone else must approve it.

**Never push directly to `main`.** Every change on `main` deploys to the live site.

If you already pushed and then rebased, update your own branch with:

```bash
git push --force-with-lease
```

Only do this on your own feature branch.

## 7. Working on the shared server

Everyone needs their own copy, so that nobody overwrites another person's work:

```bash
cd ~
git clone https://github.com/AlexFar10/LandCheck.git
cd LandCheck
git switch dev
python3 -m venv --copies .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Server rules:

- Work only in your own home folder.
- Keep your own `.venv` and `.env`.
- Do not change Docker, Coolify, firewall or system settings unless that is your assigned task.
- Do not run coding agents in approval-bypass modes such as `codex --yolo`.
- Do not use ports 80, 443, 3000, 6001, 6002, 8000 or 8080. The platform uses or may use them.
- Bind development servers to `127.0.0.1`.

Use your assigned ports:

| Person | API port | Frontend port |
|---|---:|---:|
| Raul | 18001 | 15171 |
| Ceca | 18002 | 15172 |
| Bianca | 18003 | 15173 |
| Alexandra | 18004 | 15174 |
| Emilia | 18005 | 15175 |
| Stefana | 18006 | 15176 |
| Alexandru | 18007 | 15177 |

To open a server app in your own browser, use an SSH tunnel:

```bash
ssh -L 15171:127.0.0.1:15171 -L 18001:127.0.0.1:18001 <user>@<server>
```

Replace the ports with yours. Get the server address from the team's private notes.

## 8. Running the full app

The API and the web app run in two terminals. The web dev server proxies `/api` and `/health` to the API on `PORT`, so the browser sees one origin, as in production. No CORS setup is needed.

```bash
# Terminal 1: API on http://127.0.0.1:3000 (docs at /docs)
. .venv/bin/activate
uvicorn landcheck.api.main:app --reload --host 127.0.0.1 --port 3000

# Terminal 2: web app on http://127.0.0.1:5173
cd web
npm ci
npm run dev -- --host 127.0.0.1
```

Open http://127.0.0.1:5173. You should see an OpenStreetMap basemap centred on Pechea, with the attribution in the bottom-right corner, a dashed sample coverage boundary, and a purple **SAMPLE DATA** banner in the side panel.

Check the API directly:

```bash
curl http://127.0.0.1:3000/health
curl "http://127.0.0.1:3000/api/v1/layers"
curl "http://127.0.0.1:3000/api/v1/zones?bbox=27.70,45.55,27.90,45.70"
curl "http://127.0.0.1:3000/api/v1/zones/sample_flood_history_v0-0001"
```

If the API is not running, the side panel shows "Cannot reach the Land Check API" instead of the layer list.

To call the API directly instead of through the proxy, set both `VITE_API_URL=http://127.0.0.1:3000` and `LANDCHECK_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173` in `.env`, then restart both apps.

`/health` reports `"dataset_id": "sample-fixture"` and `"sample": true`. Everything the API returns today is invented sample data from `landcheck/api/fixtures/sample/`. Set `LANDCHECK_DATASET_DIR` to serve a real dataset once one exists.

`python -m landcheck.api` starts the API the way production does: on `0.0.0.0` and port `PORT` (default 3000). Use it only in a container, not on the shared server.

**On the shared server,** port 3000 is reserved. Put your assigned API port in your own `.env` as `PORT=18001` (example for Raul), so the web proxy follows it, then run:

```bash
uvicorn landcheck.api.main:app --reload --host 127.0.0.1 --port 18001
cd web && npm run dev -- --host 127.0.0.1 --port 15171
```

### Checks before a PR

```bash
pytest
cd web && npm run lint && npm test && npm run build
```

To test the production container, see [Step 4 of the deployment plan](DEPLOYMENT.md#step-4-test-the-container-locally).

## 9. Common problems

| Problem | Fix |
|---|---|
| `No module named landcheck` | Activate `.venv` and run `pip install -e ".[dev]"` |
| `No module named fastapi` | Reinstall with `pip install -e ".[dev]"`. The `dev` extra now includes the API |
| Web app shows "Request to /health failed (502)" or similar | The API is not running, or `PORT` in `.env` does not match the API's port |
| `/health` returns 503 with `"status": "error"` | `LANDCHECK_DATASET_DIR` points to a missing or invalid dataset. The API log says why |
| Every file shows as modified in WSL | The clone is shared with Windows. Clone inside WSL, or run `git config core.autocrlf true` in that checkout |
| `pip` fails with "No space left on device" | Free disk space, or use a clone on a drive with space |
| Port is already in use | Use your assigned port |
| `git pull --ff-only` fails | Commit or stash your work, then rebase it on `origin/dev` |
| CI failed on your PR | Open the failed job's logs, fix it on your branch and push again |

## 10. Where to read more

- [Product requirements](PRD.md)
- [Deployment and CI](DEPLOYMENT.md)
- [Agent and contributor rules](../AGENTS.md)
