# Code Quality Review — Results

**Date:** 2026-11-13
**Scope:** `CODE_QUALITY_ROADMAP.md`, phases 1–6
**Outcome:** linting and refactoring complete; CI/CD and documentation phases not started.
49 files changed. 23 bugs found and fixed, most of them invisible before this pass.

---

## Status against the roadmap

| Phase | State |
|---|---|
| 1. Audit existing code | **Done** |
| 2. Linting configs (Python / Go / React) | **Done** |
| 3. Pre-commit hooks | **Deliberately skipped** — see *Decisions* |
| 4. CI/CD integration | **Not done** |
| 5. Codebase refactoring | **Done** |
| 6. Documentation | **Partly** — README corrected; the separate guides were not written |

Phases 4 and 6 are the remaining work. Everything else is finished and verified.

---

## Linting: before and after

| | Config before | Violations before | Violations now |
|---|---|---|---|
| Python (24 files, ~2.8k lines) | none | **127** | **0** |
| Go (14 files, ~1.5k lines) | none | **29** + 7 unformatted files | **0** |
| React (8 files, ~1.4k lines) | `.oxlintrc.json` | **12** | **3** (known, documented below) |

**Tooling added**

- `backend/pyproject.toml` — one `[tool.ruff]` block replacing the roadmap's pylint + black + isort + flake8 + mypy stack. Ruff does lint, format and import sorting in a single binary.
- `go-search/.golangci.yml` — errcheck, govet, ineffassign, staticcheck, unused, with `exclude-functions` for deferred closers.
- `frontend/.oxlintrc.json` — already existed but **was not tracked by git** (see bug 1).

Every rule that is switched off carries a comment saying why. Where a rule is simply wrong for this codebase (`BLE001` on FastAPI handlers that catch `Exception` to return a 500) the config says so rather than contorting the code to satisfy it.

---

## Bugs found and fixed

### Critical — the feature did not work at all

| # | Bug | Effect |
|---|---|---|
| 1 | `.gitignore` had a bare `*.json`, so `frontend/package.json`, `package-lock.json` and `.oxlintrc.json` were never committed | **A fresh clone could not build the frontend.** The same rule was also the only thing hiding an 87 MB model cache from git |
| 2 | `ingest_anime.py` wrote **hash-seeded random vectors** into a `TEXT` column, while `/api/search/semantic` queried it with the pgvector `<=>` operator against real sentence-transformer embeddings — on a stock `postgres:15` image with no `vector` extension | Semantic search could never return a meaningful result. Four separate definitions of the same table disagreed with each other |
| 3 | Four queries in `anime.py` selected `a.studios`, a column that does not exist (studios live in `studios` + `anime_studios`) | Every query raised, was caught, and fell through to `MOCK_ANIME` — **the entire site served 3 hardcoded anime** while 250 sat unreachable in the database |
| 4 | `MOCK_ANIME` fallback returned fake data with HTTP 200 on any failure; `Title.jsx` had its own `defaultTitle` doing the same | Bug 3 was invisible for weeks. `/title/<anything>` showed Steins;Gate |
| 5 | `ingest_anime.py` never created `chat_history`, `search_history`, `processed_messages` or `search_engagement` | Chat history, search logging, consumer idempotency and engagement ranking all wrote to tables that did not exist |
| 6 | The Go service called the Python semantic route with `http.Get`; the route is `@router.post` | **405 on every call.** `/api/search/anime` had never worked |
| 7 | `decide_node` passed the **whole user message** as the database query (`title ILIKE '%suggest a mecha anime%'`) | The chat agent's database tool returned nothing for any conversational phrasing, so every answer came from the model's memory instead of the catalogue |

### Data loss and silent failure

| # | Bug | Effect |
|---|---|---|
| 8 | `save_chat_message()` was defined and **never called** — chat was published to Kafka and nowhere else | With no broker, conversations vanished. Now a fallback on publish failure |
| 9 | `AnimeContextID int` in the Go event struct: JSON `null` unmarshals to `0` | Stored as `0`, but history filters on `anime_context_id IS NULL`, so the **Chat tab could never load its own history**. Now `*int` |
| 10 | `kafka_producer` was cached *before* `start()` | A failed start poisoned the global permanently; every later send failed with no recovery |
| 11 | Unchecked `SendToDLQ`, `CommitMessages` and `Close` in both consumers | A failed dead-letter send silently dropped the message. Offsets are now committed only once a message is safely handled |
| 12 | Both consumers used the same Kafka consumer group | Kafka gave each message to **one** of them, so either the DB write or the search indexing happened, never both |
| 13 | `INSERT INTO processed_messages (..., offset, ...)` — `offset` is a reserved word in Postgres | Syntax error on every message, swallowed by a "non-critical" log line. Idempotency never recorded |
| 14 | `DO UPDATE SET count = count + 1` — ambiguous column reference | The engagement upsert failed on every message, hidden behind a log line blaming a missing table |
| 15 | `json.Unmarshal` return discarded twice in `handlers/search.go` | A backend error was served as **HTTP 200 with `null`** |
| 16 | Unbuffered channels in `ConcurrentSearch` | Both goroutines leaked on every request timeout |
| 17 | `json.Marshal` error discarded in `SendToDLQ`; same for `anime_references` in the DB consumer | Empty dead-letter records and `"null"` written to the database, both reported as success |
| 18 | Bare `except: pass` on chat history JSON decoding | Malformed rows disappeared silently |

### Correctness and configuration

| # | Bug | Effect |
|---|---|---|
| 19 | `req.Query` concatenated into a URL unescaped (2 sites) | A query containing `&` or `#` rewrote the request to the backend |
| 20 | `http://localhost:8000` hardcoded in 4 Go call sites | Inside Docker, `localhost` is the Go container — every backend call fails under compose. Now `PYTHON_API_URL` |
| 21 | 4 hardcoded `http://localhost:8000` in the frontend bypassing `VITE_API_URL`; `Browse` searched `/api/search/anime`, a **Go** route, on the Python backend | Chat history and Browse search broke outside local dev; Browse's search box had always returned 404 |
| 22 | Genre matching used `a.genres && ARRAY[query]` — case-sensitive against capitalised genres | `mecha` found nothing, `Mecha` found three |
| 23 | `/api/search` ordered by rating alone | Searching `hunter` put Chainsaw Man (plot mentions "devil hunter", 9.0) above Hunter x Hunter (title match, 8.9). Title matches now rank first |

Plus: a duplicate `/debug/db-check` route (26 dead lines), a connection leak on every error path in that handler, `os.getenv("PORT", 8000)` returning an `int` default where every other path returns `str`, six implicit `Optional` type hints, and seven root-logger calls replaced with a module logger.

---

## Dead code removed

| File | Lines | Why |
|---|---|---|
| `backend/app/database.py` | 66 | Zero importers; held an obsolete 2-table schema |
| `backend/scripts/fetch_anime.py` | 100 | Superseded — yet `README.md` told you to run it |
| `backend/scripts/fetch_anime_simple.py` | 183 | Referenced nowhere |
| `design-preview.html` | 60 KB | Referenced by no file |
| `MOCK_ANIME` + `AnimeResponse` in `anime.py` | 36 | Fake data served on failure |
| `defaultTitle` in `Title.jsx` | 8 | Same, on the frontend |
| `embeddingAPI` / `recommendAPI` in `api.js` | 30 | Exported, imported nowhere |
| `handleSearch` + `searchQuery` in `Explore.jsx` | 18 | The page has no search box |

`app/utils/claude_agent.py` was on the first list and **removed from it after checking** — `langgraph_agent.py` imports it lazily at two call sites.

### Duplication merged

The two Kafka consumers were the same file twice: identical `Start` loops and `processWithRetry`, differing only in the per-message work. They now share `consumers/consumer.go`, with each consumer reduced to a constructor plus its own handler function.

---

## Tests

The repository had **none**. It now has two suites covering the code where a mistake is expensive:

- `go-search/consumers/consumer_test.go` — `shouldCommit` across its three cases, plus a test that drives a real message through the whole `Start` loop with fake reader and writer. Removing the commit guard makes it fail with *"committed 1 messages, want 0 — the message would be lost"*.
- `backend/tests/test_extract_terms.py` — 5 cases on the query parser. Stdlib `unittest`, **no new dependency**: `python -m unittest discover -s tests`.

Both suites were checked against a deliberate regression to confirm they actually fail when the logic breaks.

---

## How this was verified

Not by reading. Every claim above was executed:

- Postgres with pgvector in a throwaway container, all 250 anime ingested with real embeddings
- The Python API, the Go service and the Vite dev server running together
- Redpanda broker, with the full chat → Kafka → consumer → Postgres path driven end to end
- The frontend driven in headless Chromium (Playwright): Browse, search, Explore, title pages and the chat modal, asserting on rendered titles, poster URLs and network calls, with console errors counted
- Four real chat messages through OpenRouter to confirm the agent reaches the database

Bug 3 (the mock-data fallback) was found **only** because of the browser run — every API-level check passed while the site served fake content.

Final state: `ruff` clean · `compileall` clean · 5 Python tests pass · `gofmt`/`go vet`/`go build` clean · `golangci-lint` 0 issues · Go tests pass · `npm run build` clean · 3 oxlint warnings.

---

## Decisions worth knowing

**Ruff instead of five tools.** The roadmap specified pylint, black, isort, flake8 and mypy. Ruff covers the first four in one binary and one config block. Mypy was left out: there is no type-hint baseline, so it would produce noise rather than findings.

**oxlint instead of ESLint + Prettier.** Already installed and working; adding `.eslintrc.js`, `.prettierrc` and a TypeScript migration would have been a second toolchain for the same job.

**CI instead of pre-commit hooks.** Hooks require every contributor to run `pre-commit install` and are a second place to maintain the same rule list. One GitHub Actions workflow is the gate. **That workflow has not been written** — it is the main outstanding item.

**Lighter golangci config than `~/Qortex/qortex/golangci.yml`.** That config's `gocritic` / `revive` / `gosec` set would bury this repo in findings with no test suite to absorb the churn.

---

## Still open

1. **CI workflow (roadmap phase 4).** Nothing runs the linters automatically. The three commands are `ruff check .`, `golangci-lint run ./...` and `npm run lint`.
2. **`docker compose up` does not work.** Four separate reasons: the dead `anime_db` and `anime_kafka` containers hold those names (both crashed on a full Docker disk, so they hold no data); compose reads `${OPENROUTER_API_KEY}` from a root `.env` that does not exist, so the containerised backend gets a blank key; nothing runs the ingest step, so the database comes up empty; and with no `.dockerignore`, `COPY . .` pulls 1.2 GB of `venv/` and 87 MB of `models/` into the image.
3. **3 frontend warnings** — `set-state-in-effect` in `Chat.jsx` (fetch on mount, benign) and twice in `Explore.jsx`, where filtered results are derived into state. The Explore one is genuinely derivable during render, but rewriting it risks the pagination logic.
4. **Documentation sprawl.** 17 markdown files at the repo root, ~6,300 lines against ~5,700 lines of code, contradicting each other on which ingest script to run. `README.md` and `PHASE_1_SETUP.md` were corrected; the rest were not touched.
5. **Connection pooling.** 22 hand-rolled connect/use/close blocks across the backend routes, one per request, with no pool. Fine for a portfolio, it will not survive real traffic. This is also why the leak in `debug_db` existed — there is no shared place for it to be correct once.
6. **`backend/.env` sets `ENVIRONMENT='production'`**, so local runs report themselves as production to Sentry and PostHog.

---

## Running it

```bash
# database + broker
docker run -d --name anime_db_pgvector -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=anime_db -p 5432:5432 pgvector/pgvector:pg15
docker run -d --name anime_kafka_rp -p 9092:9092 redpandadata/redpanda:latest redpanda start \
  --overprovisioned --smp 1 --memory 1G --reserve-memory 0M --node-id 0 --check=false \
  --kafka-addr PLAINTEXT://0.0.0.0:9092 --advertise-kafka-addr PLAINTEXT://localhost:9092

# data (required — creates the schema and the embeddings)
cd backend && ./venv/bin/python scripts/ingest_anime.py

# services
cd backend && KAFKA_BROKERS=localhost:9092 ./venv/bin/python -m uvicorn main:app --port 8000
cd go-search && PORT=8080 PYTHON_API_URL=http://localhost:8000 KAFKA_BROKERS=localhost:9092 \
  REDIS_URL=redis://localhost:6379 \
  DATABASE_URL="postgres://postgres:password@localhost:5432/anime_db?sslmode=disable" go run .
cd frontend && VITE_API_URL=http://localhost:8000 VITE_GO_SEARCH_URL=http://localhost:8080 npm run dev
```

Then open <http://localhost:5173>.

### Checks

```bash
cd backend    && ruff check . && python -m unittest discover -s tests
cd go-search  && gofmt -l . && go vet ./... && golangci-lint run ./... && go test ./...
cd frontend   && npm run lint && npm run build
```
