# Roadmap

Open work only. What is already built is in [HISTORY.md](HISTORY.md).

Items carried over from the old roadmap were checked against the code first —
similar-anime recommendations, trailer embedding, filter badges and the
Makefile were all listed as outstanding but are implemented, so they are gone
from this list.

---

## Infrastructure

**`docker compose up` does not work.** Four separate reasons:

1. The dead `anime_db` and `anime_kafka` containers hold those names. Both
   crashed on a full Docker disk, so they hold no data — `docker rm` them.
2. Compose reads `${OPENROUTER_API_KEY}` from a `.env` at the project root,
   which does not exist; the keys live in `backend/.env`. The containerised
   backend therefore starts with a blank key and chat is dead. Fix:
   `env_file: ./backend/.env` on `python-backend` and `go-search`.
3. Nothing runs `ingest_anime.py`, so the database comes up empty. Add a
   one-shot `ingest` service or document the step.
4. No `.dockerignore` anywhere, and `backend/Dockerfile` does `COPY . .` —
   which pulls 1.2 GB of `venv/` and 87 MB of `models/` into the build
   context and the image.

**`version: '3.8'`** in `docker-compose.yml` is obsolete and warns on every
command.

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
