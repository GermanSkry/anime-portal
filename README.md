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

python scripts/fetch_anime.py
python scripts/ingest_anime.py

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
├── backend/
│   ├── main.py                 # FastAPI app
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example            # Environment template
│   ├── app/
│   │   ├── config.py           # Settings
│   │   ├── database.py         # DB connection
│   │   └── routes/
│   │       ├── anime.py        # Anime endpoints
│   │       ├── search.py       # Search (Phase 2)
│   │       ├── stats.py        # Stats (Phase 2)
│   │       └── recommend.py    # AI (Phase 2)
│   ├── scripts/
│   │   ├── fetch_anime.py      # Download anime data
│   │   └── ingest_anime.py     # Load into DB
│   └── data/
│       └── anime.json          # Cached anime data
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx            # React entry
│   │   ├── App.tsx             # Router
│   │   ├── pages/
│   │   │   ├── Home.tsx        # Featured, Collections
│   │   │   ├── Dashboard.tsx   # Stats
│   │   │   ├── TitleDetail.tsx # Single anime
│   │   │   └── Chat.tsx        # AI chat
│   │   ├── components/
│   │   │   ├── AnimeCard.tsx
│   │   │   ├── FilterBar.tsx
│   │   │   └── ...
│   │   └── hooks/
│   │       ├── useAnime.ts
│   │       └── useRecommendations.ts
│   ├── package.json
│   ├── tailwind.config.ts
│   └── .env.example
│
├── docs/
│   └── architecture.md
├── README.md
├── .gitignore
└── PHASE_1_SETUP.md
```

---

## Development Status

| Phase | Status | What's Done |
|-------|--------|------------|
| **Phase 1** | ✅ DONE | Data model + PostgreSQL + trailers |
| **Phase 2** | ✅ DONE | Full-text search, semantic search, AI recommendations |
| **Phase 4** | ✅ DONE | Chat endpoint, database-first search, SerpAPI web search |
| **Phase 3** | ⏳ NEXT | React UI for chat + browse dashboard (3-4 days) |
| **Deployment** | 📋 PLANNED | Railway (backend), Vercel (frontend) |

### What's Working Right Now

**Backend (100% functional):**
- 250 anime in PostgreSQL with vector embeddings
- 3 search types: full-text, semantic, AI recommendations
- Smart chat with database-first + optional web search
- Conversation history support
- Free tier SerpAPI (250 searches/month)

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
