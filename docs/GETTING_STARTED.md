# Land Check: Getting Started

Follow this guide to pull the project, run it and start working on an issue.

## 1. What runs today

| Part | Status |
|---|---|
| Python core and tests | Works |
| Hazard modules | Stubs that return `Unknown` |
| FastAPI backend | Not built yet (LC-06) |
| React frontend | Not built yet (LC-07) |

## 2. Requirements

- Git
- Python 3.10 or newer (3.12 is recommended)
- Linux, macOS or WSL on Windows

Node.js 24 and Docker will be needed once the frontend and container are added.

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

You should see **8 passed**. The pipeline prints four results with level `Unknown`, which is correct until the modules are built.

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

These commands become available after LC-06 and LC-07. The `api` extra and `web/` folder do not exist yet.

```bash
# Terminal 1: API
. .venv/bin/activate
pip install -e ".[api,dev]"
uvicorn landcheck.api.main:app --reload --host 127.0.0.1 --port 18001

# Terminal 2: frontend
cd web
npm ci
npm run dev -- --host 127.0.0.1 --port 15171
```

To test the production container, see [Step 4 of the deployment plan](DEPLOYMENT.md#step-4-test-the-container-locally).

## 9. Common problems

| Problem | Fix |
|---|---|
| `No module named landcheck` | Activate `.venv` and run `pip install -e ".[dev]"` |
| Every file shows as modified in WSL | The clone is shared with Windows. Clone inside WSL, or run `git config core.autocrlf true` in that checkout |
| `pip` fails with "No space left on device" | Free disk space, or use a clone on a drive with space |
| Port is already in use | Use your assigned port |
| `git pull --ff-only` fails | Commit or stash your work, then rebase it on `origin/dev` |
| CI failed on your PR | Open the failed job's logs, fix it on your branch and push again |

## 10. Where to read more

- [Product requirements](PRD.md)
- [Deployment and CI](DEPLOYMENT.md)
- [Agent and contributor rules](../AGENTS.md)
