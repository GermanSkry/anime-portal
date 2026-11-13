# Build History

What was built, in order. Replaces eleven planning and status documents
(`PHASE_1_SETUP`, `PHASE_1_ENHANCED_SETUP`, `PHASE_2_PLAN`, `PHASE_2_COMPLETE`,
`PHASE_3_KAFKA_PLAN`, `PHASE_3_IMPLEMENTATION`, `PHASE_4_COMPLETE`,
`PROJECT_STATUS`, `ENHANCEMENT_PLAN`, the old `ROADMAP`, and
`CODE_QUALITY_ROADMAP`), which had grown to ~5,000 lines and contradicted each
other on basics like which ingest script to run.

Open work lives in [ROADMAP.md](ROADMAP.md). Current architecture is in
[ARCHITECTURE.md](ARCHITECTURE.md) and [DATA_MODEL.md](DATA_MODEL.md).

---

## Phase 1 — Data pipeline (Oct 2026)

AniList GraphQL → `data/anime.json` → PostgreSQL.

- 250 anime with titles, year, rating, genres, cover art, plot
- Enhanced pass added trailers, characters, relations and themes, and split
  studios into `studios` + `anime_studios`
- `scripts/fetch_anime_enhanced.py` is the surviving fetcher; two earlier
  versions were deleted in the code quality review

## Phase 2 — Backend features and AI

- FastAPI routes: anime, search, chat, stats, recommend, characters, embeddings
- Semantic search over pgvector with `all-MiniLM-L6-v2` (384 dims)
- Chat backed by a LangGraph agent that picks between a database search, a web
  search, or answering directly
- Langfuse tracing, Sentry error tracking, PostHog analytics

## Phase 3 — Go search service and Kafka

- Go/gin service on `:8080`: web search via SerpAPI, Redis caching, and a
  semantic cache that reuses a cached answer when a new query's embedding is
  within 0.78 cosine similarity of an old one
- Redpanda (Kafka API) with topics `chat.messages`, `search.updates`,
  `dlq.failed_messages`
- Two consumers off `chat.messages`: one persists chat to PostgreSQL, one
  records engagement for search ranking. Retry with exponential backoff, then
  a dead-letter queue

## Phase 4 — Frontend

React 19 + Vite, four pages: Chat, Browse, Explore, Title. Contextual chat
modal on the title page, filter controls on Explore, clickable anime
references rendered out of the agent's replies.

## Code quality review (Nov 2026)

Linting across all three languages, 23 bug fixes, first tests, CI.
See [CODE_QUALITY_REPORT.md](CODE_QUALITY_REPORT.md).

---

## A note on the documents this replaces

Several of them declared features complete that had never worked. The review
ran the system end to end and found that, at the time `PHASE_4_COMPLETE.md` and
`PROJECT_STATUS.md` both claimed success:

- the site served **3 hardcoded mock anime**, not the 250 in the database,
  because four queries selected a column that does not exist and the failure
  fell through to a mock fallback
- **semantic search** matched real embeddings against hash-seeded random
  vectors in a `TEXT` column, on a Postgres image with no `vector` extension
- **chat history** was written to a table that was never created, through a
  function that was never called
- the Go service's anime endpoint returned **405 on every call**

None of this was visible from the outside: every failure path returned HTTP 200
with plausible-looking content. The lesson worth keeping is that a document
saying "✅ COMPLETE" is a claim, not evidence — which is why the current
`CODE_QUALITY_REPORT.md` records *how* each thing was verified rather than
just that it was.
