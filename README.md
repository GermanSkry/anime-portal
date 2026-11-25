# 🎬 AnimeVibing

Search, browse and talk about anime. A catalogue of 2,500 titles with semantic
search over vector embeddings, and a chat agent that looks in the catalogue
before it answers.

| | |
|---|---|
| **App** | <https://anime-portal-gules.vercel.app> |
| **API** | <https://anime.necromemecon.party:2096> |
| **Repo** | [GermanSkry/anime-portal](https://github.com/GermanSkry/anime-portal) |

---

## What it does

**Chat** — ask for something in plain words ("a mecha anime", "something about
ninjas") and a LangGraph agent decides whether to search the catalogue, search
the web, or answer directly. It quotes real titles from the database, with
ratings, and links them.

**Browse** — curated rows: highest rated, most recent, and a few genres. The
search box and the filters under it — rating, genre, year, studio — go to one
endpoint together, so a text search and a filter combine and reach all 2,500
titles.

**Explore** — the catalogue as a similarity map. 120 nodes, one per franchise,
coloured by genre and joined to what they are closest to by plot. Pick a title
to see its five closest outside its own franchise; double-click to redraw the
map around it.

**Title pages** — cover, studio, rating, genres, synopsis, trailer, the rest
of the franchise in watch order, the closest titles by plot, and a chat window
scoped to that anime.

### Search, three ways

| | |
|---|---|
| Full-text | title and plot, with filters. Title matches rank above plot matches |
| Semantic | your description against 384-dimension embeddings of every plot, through pgvector. "giant robots piloted by teenagers" finds Gunbuster |
| Web | SerpAPI, for anything newer than the catalogue |

---

## How it fits together

```
browser ──► Vercel (React build)
   └──────► Cloudflare ──► nginx, TLS ──┬── /api/search/{web,anime,concurrent,history,stats} ──► go-search
                                        └── /api/…                                           ──► python-api
                                                                                                   │
                                   postgres + pgvector · redis · redpanda ──────────────────────────┘
```

The Python API owns the catalogue, embeddings and chat. The Go service owns web
search, its Redis cache and the Kafka consumers. A chat message is published to
Redpanda and written to Postgres by a Go consumer, with a retry and a
dead-letter queue; if the broker is down the API writes it directly instead.

| Layer | |
|---|---|
| Frontend | React 19 + Vite, plain CSS, deployed on Vercel |
| API | Python 3.13 + FastAPI |
| Search service | Go 1.21 + gin |
| Database | PostgreSQL 15 + pgvector (HNSW cosine index) |
| Cache / events | Redis · Redpanda (Kafka API) |
| Chat | Claude Haiku 5.5 via OpenRouter, orchestrated with LangGraph |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2`, 384 dimensions, computed locally |
| Web search | SerpAPI, falling back to canned results when the quota or key is unavailable |
| Data source | AniList GraphQL |
| Monitoring | Sentry · PostHog · Langfuse |
| Hosting | Vercel (frontend) + a €5/month Hostinger VPS (everything else) |

---

## Running it locally

**Prerequisites** — Docker, Python 3.13, Node 20+, Go 1.21+.

```bash
docker compose up -d postgres redis redpanda

cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # OPENROUTER_API_KEY is the only one chat needs

python scripts/fetch_anime_enhanced.py   # AniList -> data/anime.json, ~4 min
python scripts/ingest_anime.py           # schema, 2,500 rows, embeddings, vector index
python -m uvicorn main:app --port 8000
```

```bash
cd go-search && go run .        # :8080, plus the Kafka consumers
cd frontend  && npm install && npm run dev    # :5173
```

`frontend/.env.development` is committed, so the frontend needs no setup.
Analytics keys are blank there on purpose — a local run does not report into
the live Sentry and PostHog projects.

Re-running `ingest_anime.py` is cheap and safe: it upserts on `anilist_id`,
keeps anime ids stable, and only recomputes an embedding when a plot changed.

### Checks

```bash
cd backend   && ruff check . && python -m unittest discover -s tests
cd go-search && gofmt -l . && go vet ./... && golangci-lint run ./... && go test ./...
cd frontend  && npm run lint && npm run build
```

The same three run in CI on every push and pull request.

---

## API

### Catalogue — Python, `:8000`

| | |
|---|---|
| `GET /api/anime` | list, paginated, sorted by rating / year / title |
| `GET /api/anime/{id}` | one title, 404 when it does not exist |
| `GET /api/anime/{id}/similar` | nearest by plot embedding, same list the graph draws, own franchise excluded |
| `GET /api/anime/{id}/related` | the rest of the franchise, oldest first |
| `GET /api/anime/{id}/characters` | main cast |

### Search

| | |
|---|---|
| `GET /api/search?q=&genres=&rating_min=&rating_max=&year_min=&year_max=&studios=&limit=&offset=` | full-text and filters; every parameter is optional, so either alone works |
| `POST /api/search/semantic?query_text=&limit=` | embedding similarity through pgvector |
| `POST /api/search/web` | SerpAPI, cached in Redis — **Go, `:8080`** |
| `POST /api/search/concurrent` | web and catalogue at once — **Go, `:8080`** |

### Graph

`GET /api/graph?seed_size=&collapse_franchises=` — every node and edge of the
similarity map in one response, plus the opening sample. ~236 KB gzipped, so
re-centring is a walk in memory rather than a request.

### Chat

| | |
|---|---|
| `POST /api/chat` | LangGraph agent; publishes to Kafka for persistence |
| `GET /api/chat/history?limit=&anime_id=` | this visitor's history, optionally for one title |

### Stats

`GET /api/stats/overview`, `/api/stats/by-genre`, `/api/stats/by-year`,
`/api/stats/count`.

---

## Deploying

Merge to `main`. Code Quality runs first; only if all three jobs pass does
Deploy build both images on a GitHub runner, push them to `ghcr.io` tagged with
the commit SHA, and ship them to the VPS over SSH. The frontend goes to Vercel
in parallel. Roughly a minute end to end.

The database is only re-ingested when a commit touches the data pipeline
itself, so an unrelated change never rebuilds the catalogue. A commit to
`fetch_anime_enhanced.py` also re-downloads from AniList first — a new field
is not in the server's `anime.json`, so ingesting the old file would only
write the same nulls. A rollback is the
Deploy workflow run by hand with an older commit SHA — that path skips the
build and only pulls.

Details, VPS port rules and the manual fallback are in
[DEPLOYMENT.md](DEPLOYMENT.md).

---

## Documentation

| | |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | how chat and browse work end to end |
| [DATA_MODEL.md](DATA_MODEL.md) | database schema |
| [DEPLOYMENT.md](DEPLOYMENT.md) | what runs where, VPS ports, shipping a change |
| [ROADMAP.md](ROADMAP.md) | what is still open, and the known trade-offs |
| [HISTORY.md](HISTORY.md) | what was built, in order |
| [CODE_QUALITY_REPORT.md](CODE_QUALITY_REPORT.md) | the linting pass and the 23 bugs it surfaced |
| [docs/kafka-testing.md](docs/kafka-testing.md) | exercising the consumers locally |
| [docs/monitoring.md](docs/monitoring.md) | Sentry, PostHog and Langfuse setup |

---

## Environment

**`backend/.env`** — see `backend/.env.example`.

```
DATABASE_URL=postgres://postgres:password@localhost:5432/anime_db
OPENROUTER_API_KEY=sk-or-v1-...
MODEL_NAME=openrouter/anthropic/claude-haiku-5.5
SERPAPI_KEY=                 # optional; without it web search returns canned results
KAFKA_BROKERS=localhost:9092
SENTRY_DSN=                  # optional
POSTHOG_API_KEY=             # optional
ENVIRONMENT=development      # keep this out of production locally
```

**`frontend/.env.development`** is committed and needs no editing.
`frontend/.env.production` carries the deployed API URL and the public PostHog
and Sentry keys.

---

## License

MIT

## Author

[German Skrylnikov](https://github.com/GermanSkry) — Backend/AI Engineer

A portfolio project: three services in two languages, event streaming with a
dead-letter queue, local vector search, an LLM agent with tool use, linting and
tests in CI, and a deploy pipeline that builds images on a runner and ships
them to a VPS.
