# 🎬 Anime Portal

A full-stack web application for discovering, searching, and getting AI-powered recommendations for anime.

**Live:** Coming soon on Vercel + Railway  
**GitHub:** [germanskrylnikov/anime-portal](https://github.com/germanskrylnikov/anime-portal)

---

## Features

- 🔍 **Interactive Anime Search** — Filter by genre, year, studio, rating
- 📊 **Analytics Dashboard** — Visualize trends, popular genres, studios
- 🤖 **AI Recommendations** — Claude-powered anime suggestions with web search
- 💬 **Chat Interface** — Talk to Claude about anime preferences
- 📱 **Responsive Design** — Works on mobile, tablet, desktop
- ⚡ **Fast Semantic Search** — PostgreSQL pgvector for intelligent queries

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18 + TypeScript + Tailwind CSS (Vercel) |
| **Backend** | Python FastAPI (Railway) |
| **Database** | PostgreSQL + pgvector (Railway) |
| **AI** | Claude API (Anthropic) |
| **Data** | AniList API |

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
- `GET /api/anime` — List anime (paginated, sortable)
- `GET /api/anime/{id}` — Get single anime details
- `GET /api/anime/stats/count` — Total anime count

### Search (Phase 2)
- `GET /api/anime/search?q=...` — Full-text search
- `POST /api/anime/semantic-search` — Semantic search by description

### Stats (Phase 2)
- `GET /api/stats` — Dashboard statistics

### Recommendations (Phase 2)
- `POST /api/recommend` — AI recommendations based on preferences
- `POST /api/search-and-summarize` — Get latest news about anime

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

## Development Phases

1. **Phase 1: Data Pipeline** ✅ In progress
   - Fetch anime data from AniList
   - Set up PostgreSQL + pgvector
   - Basic API endpoints

2. **Phase 2: Backend Core** (Next)
   - Search & filter endpoints
   - Semantic search (pgvector)
   - Dashboard stats
   - Claude AI agent

3. **Phase 3: Frontend** (Week 2)
   - React app structure
   - Pages & components
   - API integration

4. **Phase 4: Design Polish** (Week 2)
   - Tailwind styling
   - Mobile responsive
   - Micro-interactions

5. **Phase 5: Deploy** (Week 3)
   - Railway (backend)
   - Vercel (frontend)
   - Portfolio framing

---

## Environment Variables

### Backend (.env)
```
DATABASE_URL=postgres://user:pass@localhost:5432/anime_db
CLAUDE_API_KEY=sk-ant-...
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
