# 🎬 Anime Portal

A full-stack web application for discovering, searching, and getting AI-powered recommendations for anime.

**Live:** Coming soon on Vercel + Railway  
**GitHub:** [germanskrylnikov/anime-portal](https://github.com/germanskrylnikov/anime-portal)

---

## Features

- 🔍 **Interactive Anime Search** — Full-text + semantic search by description
- 📊 **250+ Anime Database** — Stored locally with vector embeddings
- 🤖 **AI Recommendations** — Claude analyzes preferences and ranks recommendations
- 💬 **Smart Chat Interface** — Claude with database-first search + real-time web search
- 🌐 **Web Search Integration** — SerpAPI for trending anime & news (saves quota smartly)
- ⚡ **Fast Semantic Search** — PostgreSQL pgvector for intelligent similarity queries
- 📱 **Responsive Design** — Works on mobile, tablet, desktop (frontend coming soon)

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18 + TypeScript + Tailwind CSS (Vercel) |
| **Backend** | Python FastAPI (Railway) |
| **Database** | PostgreSQL + pgvector (Railway) |
| **AI Chat** | Claude Haiku via OpenRouter (cost-effective) |
| **Web Search** | SerpAPI (Google Search) + DuckDuckGo fallback |
| **Embeddings** | sentence-transformers (local, 384-dim vectors) |
| **Data Source** | AniList GraphQL API |

---

## Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL (local or Docker)
- Node.js 18+ (for frontend)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env with your DATABASE_URL and CLAUDE_API_KEY

python scripts/fetch_anime_enhanced.py   # downloads data/anime.json from AniList
python scripts/ingest_anime.py           # creates the schema + embeddings

python main.py  # Runs on http://localhost:8000
```

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local with VITE_API_URL=http://localhost:8000

npm run dev  # Runs on http://localhost:5173
```

---

## API Endpoints

### Anime
- `GET /api/anime` — List anime (paginated, sortable by rating/year)
- `GET /api/anime/{id}` — Get single anime details + trailer

### Search (Phase 2)
- `GET /api/search?q=...&genres=...&year_min=...` — Full-text search with filters
- `POST /api/search/semantic?query_text=...` — Semantic search (AI-powered similarity)

### Recommendations (Phase 2)
- `POST /api/recommend` — Claude analyzes preferences and ranks anime

### Chat (Phase 4) ⭐ NEW
- `POST /api/chat` — Claude chatbot with smart search
  - Database-first search (saves web quota)
  - Optional web search for trending/current info
  - Conversation history support
  - Real-time SerpAPI integration

### Stats
- `GET /api/stats` — Dashboard statistics

---

## Project Structure

```
anime-portal/
├── backend/                     # FastAPI + Postgres/pgvector
│   ├── main.py                  # app entrypoint, Sentry/PostHog/Kafka wiring
│   ├── requirements.txt
│   ├── pyproject.toml           # ruff config (lint + format + imports)
│   ├── app/
│   │   ├── config.py            # settings from env
│   │   ├── routes/              # anime, search, chat, stats, recommend,
│   │   │                        #   characters, embeddings
│   │   └── utils/               # langgraph_agent, claude_agent, embeddings,
│   │                            #   web_search, langfuse_tracer
│   ├── scripts/
│   │   ├── fetch_anime_enhanced.py   # AniList -> data/anime.json
│   │   ├── ingest_anime.py           # anime.json -> Postgres + embeddings
│   │   ├── update_plots.py
│   │   └── update_trailers.py
│   └── data/anime.json          # fetched, gitignored
│
├── go-search/                   # Go search service + Kafka consumers
│   ├── main.go                  # gin API on :8080
│   ├── .golangci.yml
│   ├── handlers/ services/ cache/ db/ kafka/ consumers/ utils/
│
├── frontend/                    # React 19 + Vite
│   ├── src/
│   │   ├── App.jsx              # router
│   │   ├── pages/               # Chat, Browse, Explore, Title
│   │   ├── components/          # ChatModal, MessageRenderer
│   │   └── services/api.js      # all backend calls (uses VITE_API_URL)
│   ├── .oxlintrc.json
│   └── package.json
│
├── docker-compose.yml           # postgres(pgvector), redis, redpanda
├── Makefile
└── README.md
```

---

## Documentation

| | |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | How chat and browse work end to end |
| [DATA_MODEL.md](DATA_MODEL.md) | Database schema |
| [HISTORY.md](HISTORY.md) | What was built, in order |
| [ROADMAP.md](ROADMAP.md) | What is still open |
| [CODE_QUALITY_REPORT.md](CODE_QUALITY_REPORT.md) | Linting, the 23 bugs found, how they were verified |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Hosting options |
| [docs/kafka-testing.md](docs/kafka-testing.md) | Exercising the consumers locally |
| [docs/monitoring.md](docs/monitoring.md) | Sentry, PostHog, Langfuse setup |

## Status

All four phases are implemented: data pipeline, backend and AI, the Go search
service with Kafka consumers, and the React frontend. 250 anime with real
`all-MiniLM-L6-v2` embeddings, three search types (full-text, semantic,
AI recommendations), and a LangGraph chat agent that searches the catalogue
before answering.

Verified end to end in a browser, against live Postgres, Redpanda and both
services — see [CODE_QUALITY_REPORT.md](CODE_QUALITY_REPORT.md) for what that
run found and fixed. Known gaps, including `docker compose up`, are in
[ROADMAP.md](ROADMAP.md).

---

## Environment Variables

### Backend (.env)
```
# Database
DATABASE_URL=postgres://user:pass@localhost:5432/anime_db

# Claude API (via OpenRouter - cheaper alternative)
OPENROUTER_API_KEY=sk-or-v1-...
MODEL_NAME=anthropic/claude-haiku-5.5

# Web Search (SerpAPI - 250 free searches/month)
SERPAPI_KEY=your_serpapi_key_here

# Server
PORT=8000
ENVIRONMENT=development
```

### Frontend (.env.local)
```
VITE_API_URL=http://localhost:8000
```

---

## Contributing

This is a personal portfolio project. Feel free to fork and build your own version!

---

## License

MIT

---

## Author

[German Skrylnikov](https://github.com/germanskrylnikov)  
Backend/AI Engineer | Data Science → Full-Stack

Built as a portfolio project showcasing:
- Full-stack architecture (React + FastAPI + PostgreSQL)
- AI integration (Claude API with web search)
- Data visualization & design
- Deployment automation (Vercel + Railway)
