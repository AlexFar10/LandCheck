# VPS Agent Task: Run Land Check CI on Coolify

**For:** the coding agent running on the project VPS.

**Goal:** get the `dev` branch building in a new Coolify **staging** application, so the lint and test results appear in its deployment log. Production must not change.

Work through the steps in order. At every **APPROVAL GATE**, stop and wait for the person running this session.

## Before you start

1. If this session bypasses approvals (for example `--yolo` or `--dangerously-skip-permissions`), **stop now**. Ask the person to restart you with approvals on.
2. Read [`AGENTS.md`](../AGENTS.md) and [`docs/DEPLOYMENT.md`](DEPLOYMENT.md).
3. Tell the person the plan in two or three sentences.

## Hard limits

Do not do any of these unless the person explicitly approves that specific action in this session:

- Change, redeploy, stop or delete the existing production application
- Push, merge or commit to any branch
- Edit `/etc/docker/daemon.json`, or restart Docker, Coolify or Traefik
- Change firewall, SSH, user, sudo or system settings
- Run `docker system prune`, or remove any image, container, volume or network this task did not create
- Search for, read, copy or print secrets, including Coolify's database, `/data/coolify/source/.env`, API tokens and SSH keys
- Edit tests, lint rules or the Dockerfile to make CI pass
- Put server addresses, ports, domains, tokens or logs containing them in the repository, an issue or a PR. **This repository is public.**

If a step fails, stop and report the first real error. Do not improvise a workaround.

## Step 1: Sync the code

```bash
cd ~/LandCheck
git status --short
git fetch origin
```

If `git status --short` prints anything, **stop** and ask the person how to handle those changes. Otherwise:

```bash
git switch dev
git pull --ff-only
git log -1 --oneline
```

## Step 2: Check the server (read-only)

```bash
docker version --format 'client {{.Client.Version}} server {{.Server.Version}}'
docker buildx version
df -h / /var/lib/docker
free -h
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
docker network ls --format '{{.Name}}' | grep -x coolify
```

Record the production app's container name, image and status so you can compare them in Step 6. A missing `buildx` is not a failure on its own.

**APPROVAL GATE** if the disk has less than 5 GB free.

## Step 3: Test Docker DNS

The last Coolify deployment failed because the build could not resolve DNS.

```bash
docker image inspect busybox >/dev/null 2>&1 && echo "busybox already present" || echo "busybox not present"
docker run --rm busybox nslookup pypi.org
docker run --rm --network coolify busybox nslookup pypi.org
```

Skip the last command if the `coolify` network does not exist. If this task pulled `busybox`, remove it at the end with `docker rmi busybox`.

**APPROVAL GATE** if either lookup fails. Report the output and the result of `resolvectl status`, then propose a fix. Do not apply it. A Docker restart briefly stops every container on the server.

## Step 4: Build and test the image

```bash
ss -ltn | grep ':13000 ' && echo "port 13000 is busy"
docker build --target ci -t landcheck:vps-verify-ci .
docker build -t landcheck:vps-verify .
docker run -d --name landcheck-vps-verify -p 127.0.0.1:13000:3000 landcheck:vps-verify
for i in $(seq 1 30); do
  s=$(docker inspect -f '{{.State.Health.Status}}' landcheck-vps-verify)
  [ "$s" = healthy ] && break
  sleep 2
done
echo "health: $s"
curl -fsS http://127.0.0.1:13000/health
```

If port 13000 is busy, choose another free local port. If Buildx hides the output, add `--progress=plain` to the build commands.

Expected results:

- The build prints `===== CI: passed =====`
- Health is `healthy`
- `/health` returns `{"status":"ok"}`

Clean up only what this step created:

```bash
docker rm -f landcheck-vps-verify
docker rmi landcheck:vps-verify landcheck:vps-verify-ci
```

## Step 5: Create the staging app

**APPROVAL GATE.** Ask:

> The image passes on this server. May I create a new Coolify application called `landcheck-staging` from the `dev` branch? It will not touch production. You can create it in the dashboard using the settings below, or give me a Coolify API token for this session.

Do not look for a token yourself. Do not save one to a file or print it.

| Setting | Value |
|---|---|
| Name | `landcheck-staging` |
| Repository | `AlexFar10/LandCheck` |
| Branch | `dev` |
| Build Pack | **Dockerfile** |
| Base Directory | `/` |
| Dockerfile Location | `/Dockerfile` |
| Ports Exposes | `3000` |
| Docker build target | Empty |
| Health check | Use the Dockerfile `HEALTHCHECK` |
| Auto Deploy | Off for the first deployment |
| Environment variable | `PORT=3000` |
| Domain | A separate staging domain, never the production one |

## Step 6: Deploy and verify

Start one deployment of `landcheck-staging`, then confirm:

- [ ] The deployment log contains `===== CI: lint =====`
- [ ] The deployment log contains `===== CI: tests =====`
- [ ] The deployment log contains `===== CI: passed =====`
- [ ] The deployment finishes successfully
- [ ] The staging `/health` returns `{"status":"ok"}`
- [ ] The production container has the same name, image and healthy state as in Step 2

Troubleshooting:

| Symptom | Action |
|---|---|
| No `CI:` lines | Check Build Pack and build target. The step may also be cached, so ask before forcing a rebuild |
| Hostname cannot be resolved | Return to Step 3 |
| `network mode 'coolify' not supported by buildkit` | Stop and report it with [Coolify issue #9804](https://github.com/coollabsio/coolify/issues/9804) |
| Lint or test failure | Stop and report the first error. Do not edit the code |
| 502, 503 or Bad Gateway | Check Ports Exposes, the domain and container logs |

**APPROVAL GATE** before turning on Auto Deploy for staging.

## Step 7: Report

Write the report **outside the repository**:

```bash
touch ~/landcheck-vps-report.md
chmod 600 ~/landcheck-vps-report.md
```

Include:

1. Commit tested
2. Docker version and whether Buildx is present
3. DNS result, both default and on the `coolify` network
4. Local image build and health result
5. Coolify staging result and the CI lines seen
6. Confirmation that production is unchanged
7. Everything you changed on the server
8. Problems and decisions that need a person

Then give the person a short summary with the same outcome and any decision they need to make.

## Done means

The task is complete when `landcheck-staging` deploys from `dev`, its Coolify log shows `===== CI: passed =====`, its `/health` responds, and production is unchanged. Stop there. Do not start on firewall, HTTPS, production or application changes.
