# Deployment Status

**Updated:** 2026-11-18
**Backend:** live — `https://anime.necromemecon.party:2096`
**Frontend:** not deployed

---

## What is running

| Component | State | Notes |
|---|---|---|
| VPS (Hostinger, Ubuntu 24.04) | ✅ | 1 vCPU, 4 GB, 48 GB disk — 33 GB free |
| PostgreSQL + pgvector | ✅ | **250 anime, 250 embeddings, 57 studios** |
| Redis | ✅ | healthy |
| Redpanda (Kafka) | ✅ | topics created, both consumers attached |
| Python API | ✅ | `127.0.0.1:8010`, behind nginx |
| Go search service | ✅ | `127.0.0.1:8011`, behind nginx |
| nginx + TLS | ✅ | port 2096, cert valid to 16 Feb 2027 |
| Restart policy | ✅ | `unless-stopped` on all five services |
| Frontend (Vercel) | ❌ | see *Outstanding* |

Verified from the public internet:

```
/health                      200
/api/anime?limit=2           200   (Frieren, Chainsaw Man … real catalogue)
/api/anime/26                200
/api/search?q=hunter         200
/api/stats/count             200
POST /api/search/semantic    200   ("giant robots" → DARLING in the FRANXX)
POST /api/search/anime       200   (Go service → Python backend)
OPTIONS /api/search/anime    204   with Access-Control-Allow-Origin
POST /api/chat               200   (answers from the catalogue)
```

The chat message travelled the full path: API → Kafka → both consumers →
`chat_history` row and `search_engagement` entries.

---

## What was actually wrong

The previous report listed Docker as the blocker. It was four separate faults,
none of them Docker's complexity.

**1. The backend image had never been built.** `pip install` failed:

```
× Failed to build installable wheels for some pyproject.toml based projects
╰─> aiokafka
```

`aiokafka==0.10.0` has no Python 3.13 wheel and cannot compile in
`python:3.13-slim`. Bumped to `0.12.0`.

**2. Port collisions with the VPN on the same host.** Compose published the Go
service on **8001**, which is xray — the backend of the `:443` SNI stream — and
the API on **8000**, which is marzban's panel. Neither could bind, which is why
`docker compose up -d` produced no containers. Everything now binds loopback on
8010/8011, with postgres, redis and redpanda also loopback-only.

**3. Kafka was wired to addresses nothing served.** The backend had no
`KAFKA_BROKERS` at all and fell back to `localhost:9092` inside its own
container; redpanda advertised `redpanda:29092` while listening on `9092`, so
the Go consumers failed to dial it every 15 seconds. Both now use
`redpanda:9092`.

**4. The database was empty.** The earlier report recorded 250 anime ingested;
`\dt` returned *"Did not find any relations."* `anime.json` was not on the VPS
either — it is gitignored. Copied up and ingested.

Also fixed on the way: `lib/pq` requires SSL by default and the container does
not offer it, so the Go service could never have reached postgres
(`sslmode=disable`); the Go service had no CORS headers, so every browser call
from the frontend would have been blocked; and no service had a restart policy,
so nothing would survive a reboot.

**`vercel.json` could not have worked either.** Its `routes` entries used the
key `destination`, which belongs to `rewrites` — legacy `routes` take `dest` —
so the SPA fallback never applied, which is the "Cannot GET /". It also proxied
to port 8080 where nothing listens, and ran `npm run build` in a directory
where nothing had been installed.

---

## Architecture

The frontend is on Vercel; the VPS serves the API only.

```
browser ──► Vercel (static React)
   └──────► https://anime.necromemecon.party:2096   (nginx, TLS)
                ├── /api/search/{web,anime,concurrent,history,stats} → go-search :8011
                └── /api/…                                           → python-api :8010
```

Port 2096 is shared with the existing marzban vhost; nginx selects by SNI, so
the `:443` SNI stream config and the VPN are untouched. One origin serves both
services, so the frontend needs a single base URL.

---

## Outstanding

**1. Frontend.** `anime-portal.vercel.app` returns 404, there is no `.vercel`
link in the repo, no Vercel CLI installed, and GitHub records no deployments —
so it is unclear whether it ever deployed. Once the project is identified, set
both variables to the same value and redeploy:

```
VITE_API_URL        = https://anime.necromemecon.party:2096
VITE_GO_SEARCH_URL  = https://anime.necromemecon.party:2096
```

**2. A stray process is holding marzban's panel port.** `python main.py` from
the failed attempt still listens on `0.0.0.0:8000`, so
`vpn.necromemecon.party:8444` returns 404. The VPN data plane is unaffected.

```
pkill -f "python main.py"
docker restart marzban-marzban-1   # to re-bind; this also restarts xray
```

**3. The backend image is 9.76 GB.** `sentence-transformers` pulls the CUDA
torch build — roughly 5 GB of `nvidia-*` wheels onto a box with no GPU. A fix
(CPU-only wheel plus `.dockerignore`) is committed but not yet applied; it
needs a rebuild and should bring the image to ~1.5 GB.

**4. Secrets.** `ENVIRONMENT` now defaults to `production`, but check
`/opt/anime-portal/.env` — a `development` value there would still report local
runs as production to Sentry and PostHog.

---

## Operating it

```bash
ssh root@76.13.250.179
cd /opt/anime-portal

docker compose ps                      # what is up
docker compose logs -f python-backend  # API logs
docker compose logs -f go-search       # consumer logs
docker compose up -d                   # start / apply config changes
docker compose exec python-backend python scripts/ingest_anime.py   # reload data

nginx -t && systemctl reload nginx     # after editing /etc/nginx/sites-available/anime-portal
```
