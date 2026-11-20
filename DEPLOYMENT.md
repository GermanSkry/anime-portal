# Deployment

Live as of 2026-11-18. Replaces `DEPLOYMENT_GUIDE.md`, `DEPLOYMENT_STATUS.md`
and `ANIME_PORTAL_VPS_DEPLOYMENT.md`.

| | |
|---|---|
| Frontend | <https://anime-portal-gules.vercel.app> (Vercel, auto-deploys on push to `main`) |
| API | `https://anime.necromemecon.party:2096` (Hostinger VPS, behind Cloudflare) |
| Cost | €5/month, VPS only |

```
browser ──► Vercel (static React build)
   └──────► Cloudflare (proxied) ──► https://anime.necromemecon.party:2096   nginx, TLS
                ├── /api/search/{web,anime,concurrent,history,stats} → go-search  127.0.0.1:8011
                └── /api/…                                           → python-api 127.0.0.1:8010
                                                                          │
                              postgres+pgvector · redis · redpanda ───────┘  (all loopback)
```

The VPS hosts other services too. **Read `VPS ports` below before changing
anything that binds a port.**

---

## VPS ports

| Port | Owner | |
|---|---|---|
| 8000 | another service on this host | **never bind this** |
| 8001, 8443 | another service on this host | **never bind this** |
| 443 | SNI stream router (`/etc/nginx/stream.d/443.conf`) | do not add an http server here |
| 2096 | nginx | shared by SNI — the anime vhost is `server_name anime.necromemecon.party` |
| 8010, 8011, 5432, 6379, 9644 | anime portal | bound to `127.0.0.1` only |

Enforced in three places: `docker-compose.yml` publishes every port as
`127.0.0.1:<port>`; `/opt/anime-portal/.env` sets `PORT=8010`; and
`backend/main.py` binds `127.0.0.1` when run directly (the container passes
`--host 0.0.0.0` on its command line, so the deployment is unaffected).

Check after any change — every line must start with `127.0.0.1`, and none may
be 8000, 8001 or 8443:

```bash
docker ps --format '{{.Names}}' | grep '^anime_' | while read c; do docker port "$c"; done
```

---

## Deploying a change

**Frontend** — merge to `main`. Vercel builds and deploys automatically.
`frontend/.env.production` supplies the API URL, so no dashboard step. Vercel's
project root directory is `frontend/`, which is why `vercel.json` lives there
and carries only the SPA rewrite.

**Backend / Go service** — merge to `main`. `.github/workflows/deploy.yml`
waits for Code Quality to pass, builds both images on a GitHub runner, pushes
them to `ghcr.io`, then SSHes to the VPS and runs `deploy.sh`, which pulls and
restarts. The box only pulls: building the backend image here takes 15-40
minutes on one vCPU and starves everything else on the host.

Images are tagged with the commit SHA as well as `latest`, so a rollback is a
`workflow_dispatch` run of **Deploy** with an older SHA in the `tag` input —
that path skips the build entirely and only pulls.

Recreating `anime_api` costs about a minute while the embedding model loads.
The site stays up and returns empty results during that window; `deploy.sh`
waits for `/health` and fails with container logs if it never answers.

*Manual fallback*, for when CI is unavailable:

```bash
ssh root@76.13.250.179
cd /opt/anime-portal
git pull --ff-only origin main      # never `git stash -u` here: see Pitfalls
docker compose build python-backend  # or go-search; `build:` is still defined
docker compose up -d python-backend go-search
```

**Data** — ingest runs automatically on merge, but only when a commit touches
`ingest_anime.py`, `fetch_anime_enhanced.py`, `embeddings.py` or
`query_terms.py`. It is safe to run often: it upserts on `anilist_id` and only
recomputes an embedding when that title's plot changed, so an unchanged
catalogue takes seconds rather than minutes, and anime ids stay stable across
runs.

To refresh the catalogue, or to re-ingest after a change CI did not detect, run
**Deploy** by hand (Actions → Deploy → Run workflow) with:

| input | |
|---|---|
| `fetch` | re-download from AniList, ~4 min, then ingest |
| `ingest` | ingest the catalogue already on disk |

A fetch implies an ingest — new data is pointless until it is loaded. The
fetcher refuses to replace a good file with a smaller one, so a failed fetch
leaves the existing catalogue alone.

The same thing over SSH, if CI is unavailable:

```bash
docker compose exec python-backend python scripts/fetch_anime_enhanced.py   # ~4 min, AniList is rate limited
docker compose exec python-backend python scripts/ingest_anime.py
```

Rebuilds the schema and all 250 embeddings. `backend/data/anime.json` must be
present — it is gitignored, so copy it up with `scp` or regenerate it with
`scripts/fetch_anime_enhanced.py`.

---

## Operating it

```bash
docker compose ps
docker compose logs -f python-backend
docker compose logs -f go-search        # Kafka consumers log here
docker compose restart go-search

docker exec anime_db psql -U postgres -d anime_db -c '\dt'
docker exec anime_db psql -U postgres -d anime_db -c 'SELECT count(*) FROM anime;'

nginx -t && systemctl reload nginx      # after editing the vhost
docker builder prune -f                 # reclaim build cache
```

Config lives at `/etc/nginx/sites-available/anime-portal`. Secrets are in
`/opt/anime-portal/.env` (gitignored, never committed).

---

## First-time setup

Already done; recorded so it can be repeated.

**CI deploys — not yet done.** Three steps, all needing access this repository
does not have:

1. *Deploy key.* Generate a pair used for nothing else, and restrict it on the
   server to the one command it needs:

   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/animevibing_deploy -N '' -C 'github actions deploy'
   ssh-copy-id -i ~/.ssh/animevibing_deploy.pub root@76.13.250.179
   ```

   Then on the VPS, prefix that key's line in `~/.ssh/authorized_keys` with:

   ```
   command="/opt/anime-portal/deploy.sh",no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-pty
   ```

   The key can then only run the deploy, not open a shell. `deploy.sh` reads
   the requested tag out of `SSH_ORIGINAL_COMMAND`, because a forced command
   drops the client's environment.

2. *Repository secrets* (Settings → Secrets and variables → Actions):

   | name | value |
   |---|---|
   | `VPS_SSH_KEY` | contents of `~/.ssh/animevibing_deploy` (the private half) |
   | `VPS_HOST` | `76.13.250.179` |
   | `VPS_USER` | `root` |

3. *Package visibility.* The first run creates `anime-portal-backend` and
   `anime-portal-go-search` under the account's Packages. They are private by
   default, so either set both to Public — the repository is already public —
   or run `docker login ghcr.io` on the VPS with a read:packages token.

Then run **Deploy** once by hand (Actions → Deploy → Run workflow) before
trusting it on every merge, and copy `deploy.sh` up once so the first run has
it: `scp deploy.sh root@76.13.250.179:/opt/anime-portal/ && ssh root@76.13.250.179 chmod +x /opt/anime-portal/deploy.sh`.

**TLS** — issued with acme.sh, valid to 16 Feb 2027, renewed by the daily cron
at 05:17:

```bash
~/.acme.sh/acme.sh --issue --standalone -d anime.necromemecon.party
~/.acme.sh/acme.sh --install-cert -d anime.necromemecon.party --ecc \
  --fullchain-file /opt/anime-portal/certs/fullchain.pem \
  --key-file /opt/anime-portal/certs/privkey.pem \
  --reloadcmd "nginx -t && systemctl reload nginx"
```

**Firewall** — 2096 is already open. `ufw status` to confirm; nothing else
needs opening, because every service port is loopback.

**Vercel** — project `necromemecon/anime-portal`, connected to the GitHub repo,
root directory `frontend`. No environment variables are set in the dashboard;
they come from `frontend/.env.production`.

---

## Pitfalls that have actually bitten

**`git stash -u` in `/opt/anime-portal` deletes the TLS certificate.**
`certs/`, `.env.production` and `start.sh` are untracked, and `-u` sweeps
untracked files. nginx keeps serving from memory, so the damage only appears at
the next reload. `.git/info/exclude` now covers them. Use plain `git pull
--ff-only`.

**Never run `python main.py` on the VPS.** It used to bind `0.0.0.0:8000` and
take that port from the service that owns it, leaving a hung process that also
blocked `docker compose up`. It now defaults to loopback, but use compose.

**`aiokafka` must stay at a version with a cp313 wheel.** `0.10.0` has none and
cannot compile in `python:3.13-slim`, which fails the whole image build.

**torch must come from the CPU index.** The default pulls the CUDA build —
about 5 GB of `nvidia-*` wheels onto a box with no GPU. `backend/Dockerfile`
installs the CPU wheel first; the image is 2.12 GB instead of 9.76 GB.

**Both Kafka clients must agree on `redpanda:9092`.** Redpanda previously
advertised `:29092` while listening on `:9092`, and the backend had no
`KAFKA_BROKERS` at all and fell back to `localhost`.

---

## Verifying a deploy

```bash
B=https://anime.necromemecon.party:2096
curl -s -o /dev/null -w '%{http_code}\n' $B/health
curl -s "$B/api/anime?limit=1"
curl -s -X POST "$B/api/search/semantic?query_text=giant%20robots&limit=1"
curl -s -X POST "$B/api/search/anime" -H 'Content-Type: application/json' -d '{"query":"ninja"}'

U=https://anime-portal-gules.vercel.app
JS=$(curl -s $U/ | grep -oE '/assets/[^"]+\.js' | head -1)
curl -s "$U$JS" | grep -c 'necromemecon.party:2096'   # want 1
curl -s -o /dev/null -w '%{http_code}\n' $U/browse    # want 200 (SPA routing)
```

A chat message should land in the database, proving API → Kafka → consumer:

```bash
docker exec anime_db psql -U postgres -d anime_db -c 'SELECT count(*) FROM chat_history;'
```

---

## Outstanding

**The cert renewal hook points at the wrong thing.** acme.sh is configured with
`reloadcmd = cd /opt/anime-portal && docker compose restart`, but nginx serves
the certificate, not the containers. At renewal nginx would keep the old cert
until someone reloads it. Fix (needs running on the VPS):

```bash
/root/.acme.sh/acme.sh --install-cert -d anime.necromemecon.party --ecc \
  --fullchain-file /opt/anime-portal/certs/fullchain.pem \
  --key-file /opt/anime-portal/certs/privkey.pem \
  --reloadcmd "nginx -t && systemctl reload nginx"
```

**Port 2096 is still in the URL.** The hostname is proxied by Cloudflare, so
the origin IP is hidden and DDoS protection applies, but the browser still
connects on `:2096` — a visitor on a network that blocks non-standard ports
will load the site and have every API call fail.

The fix is a Cloudflare **Origin Rule** rewriting the destination port to 2096,
which lets visitors use `https://anime.necromemecon.party` with no port:

```
browser ──:443──► Cloudflare ──:2096──► nginx
```

Then drop `:2096` from both lines of `frontend/.env.production` and redeploy.
This avoids editing `/etc/nginx/stream.d/443.conf`, which is shared with
another service on the host. Without the rule, plain `:443` returns 404,
because Cloudflare reaches the origin on 443 where the SNI router does not know
this hostname.

**`docker compose` has no healthcheck on the two app services**, so `up -d`
reports success before the API can serve.

**`ENVIRONMENT` in `/opt/anime-portal/.env` is `production`** — correct here,
but the same file is the template people copy locally.
