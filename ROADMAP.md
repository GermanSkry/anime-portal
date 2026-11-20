# Roadmap

Open work only. What is already built is in [HISTORY.md](HISTORY.md).

Items carried over from the old roadmap were checked against the code first —
similar-anime recommendations, trailer embedding, filter badges and the
Makefile were all listed as outstanding but are implemented, so they are gone
from this list.

---

## Next session

Carried over from the first deployment (2026-11-18). None of these break
anything today.

**Deploy from CI instead of building on the VPS.** Implemented in
`.github/workflows/deploy.yml` and `deploy.sh`; see DEPLOYMENT.md. Still needs
the deploy key, the three repository secrets and the package visibility set —
none of which can be done from the repository.

**Fix the certificate renewal hook.** acme.sh is configured with
`reloadcmd = cd /opt/anime-portal && docker compose restart`, but nginx serves
the certificate, not the containers. At renewal nginx would keep serving the
old one. The cert runs to 16 Feb 2027, so there is time, but it is one command:

```bash
/root/.acme.sh/acme.sh --install-cert -d anime.necromemecon.party --ecc \
  --fullchain-file /opt/anime-portal/certs/fullchain.pem \
  --key-file /opt/anime-portal/certs/privkey.pem \
  --reloadcmd "nginx -t && systemctl reload nginx"
```

**Add healthchecks to python-backend and go-search.** `docker compose up -d`
reports success about a minute before the API can actually serve, because the
backend loads the embedding model at import. Without a healthcheck, a deploy
looks finished while requests still 502, and `depends_on: service_healthy`
cannot be used for anything downstream.

**Drop the port from the API URL.** The hostname is now proxied by Cloudflare,
so the origin IP is hidden, but the browser still connects on `:2096` and a
network that blocks non-standard ports breaks every API call.

A Cloudflare **Origin Rule** rewriting the destination port to 2096 lets
visitors use `https://anime.necromemecon.party` with no port. Two steps:

1. Cloudflare → Rules → Origin Rules → for `anime.necromemecon.party`, set the
   destination port to 2096
2. drop `:2096` from both lines of `frontend/.env.production`, merge, Vercel
   redeploys

This replaces the earlier plan of moving the API behind the `:443` SNI stream,
which would have meant editing a config shared with another service on the
host. The rule avoids that file entirely.

Verify before and after with `curl --resolve` against the origin, so a 522 at
the edge is not mistaken for a dead API. Confirm Origin Rules are available on
the current Cloudflare plan first.

## Infrastructure

**Compose is only configured for the server.** `docker compose up` now works
on the VPS, but a local run still needs a `.env` at the project root — the keys
live in `backend/.env` and compose reads `${OPENROUTER_API_KEY}` from the root.
`env_file: ./backend/.env` on `python-backend` and `go-search` would make a
clone work with no extra step.

**Nothing runs the ingest.** `docker compose up` brings up an empty database;
`scripts/ingest_anime.py` has to be run by hand, and `backend/data/anime.json`
is gitignored so it is not there after a clone. A one-shot `ingest` service, or
a `make` target that fetches and ingests, would close the gap.

## Backend

**Connection pooling.** 22 hand-rolled connect/use/close blocks across the
routes, one connection per request, no pool. Fine for a portfolio, it will not
survive real traffic. It is also why a leak existed in `debug_db` — there is no
shared place for the handling to be correct once.

**`ruff format` has never been run.** 19 files would change. Worth doing as a
single commit, after which the `ruff format --check` step can be added to CI.

**`backend/.env` sets `ENVIRONMENT='production'`**, so local runs report
themselves as production to Sentry and PostHog.

**Debug endpoints.** `/api/anime/debug/db-check` exposes database state with no
authentication.

## Search and chat

**Web search is unverified.** `/api/search/web` and the `search_web` tool need
`SERPAPI_KEY`; neither has been exercised. The agent also passes the whole user
message to the web search, where the database search now extracts terms first.

**The agent's term extraction is a hand-written filler list.** An unusual
phrasing can still leak a noise word into the query. It degrades ranking, not
correctness.

**Search ranking is two-tier** (title match, then rating). Within a tier it is
pure rating, so two matching titles sort by score rather than by how closely
they match.

## Frontend

**The analytics SDKs tripled the bundle.** 282 kB to 654 kB raw, 88 kB to
215 kB gzipped, from `posthog-js` and `@sentry/react`. Tracing config makes no
difference — it is the SDKs themselves. Worth revisiting if first paint starts
to matter: load `initAnalytics()` after the first render, or swap PostHog for
its lite build. Error tracking is worth the weight; the pageview autocapture
is the part that could be dropped.


**Three `set-state-in-effect` warnings.** One in `Chat.jsx` (fetch on mount,
benign) and two in `Explore.jsx`, where filtered results are derived into
state. The Explore one is genuinely derivable during render, but rewriting it
risks the pagination logic. CI is set to `--max-warnings 3`, so a fourth fails
the build.

**Browse has three genre sections** — Action, Drama, Psychological. Comedy,
Romance, Sci-Fi and Adventure are all in the data.

**The chat modal does not refetch history** when closed and reopened in the
same page view; it keeps the messages in memory. A page reload refetches.

## Testing

**Two suites, both narrow.** `consumers/consumer_test.go` covers the Kafka
commit decision and the consumer loop; `backend/tests/` covers the query
parser. Nothing covers the HTTP routes, and the Go handlers are hard to test
because the backend URL and the embedding client are resolved at construction
rather than injected.

**The DLQ path has never run against a real broker** — only against fakes.
