# Phase 1: Enhanced Data Pipeline (Option B)

## What We Built

You now have a **Phase 1+2 database schema** with support for:

### Tables Created:
1. **anime** — Main anime table with enhanced fields (seasons, themes, episode count)
2. **studios** — Production studios (deduplicated)
3. **anime_studios** — Many-to-many relationship (which studios make which anime)
4. **characters** — Character data (name, role, image)
5. **anime_characters** — Many-to-many (which characters appear in which anime)
6. **related_anime** — Anime relationships (sequels, prequels, spin-offs)
7. **embeddings** — Semantic search vectors (for AI recommendations)
8. **recommendations** — Smart recommendations (for Phase 2 AI)

### API Endpoints (Already Created):

**Anime:**
- `GET /api/anime` — List anime (paginated, sortable)
- `GET /api/anime/{id}` — Single anime details

**Characters (Phase 2-ready):**
- `GET /api/anime/{id}/characters` — Characters in anime
- `GET /api/anime/{id}/related` — Sequels, prequels, spin-offs

**Dashboard Stats:**
- `GET /api/stats/overview` — Full dashboard data (avg rating, genre distribution, top rated)
- `GET /api/stats/by-genre` — Anime by genre
- `GET /api/stats/by-year` — Anime by year

---

## Data Flow (Detailed)

### Step 1: Fetch Enhanced Data
```bash
cd backend
python scripts/fetch_anime_enhanced.py
```

**What happens:**
- Connects to AniList GraphQL API
- Fetches 250 anime with:
  - Basic info (title, year, rating, plot, genres, studios)
  - **NEW**: Themes, episodes, season, status
  - **NEW**: Top 5 characters per anime (with images, roles)
  - **NEW**: Related anime (sequels, prequels, spin-offs)

**Output:** `data/anime.json` (includes nested characters + relations data)

### Step 2: Ingest into PostgreSQL
```bash
python scripts/ingest_anime.py
```

**What happens:**
- Creates enhanced schema (8 tables with proper relationships)
- Creates indexes for fast queries
- Inserts anime into main table
- De-duplicates and inserts studios
- Generates semantic embeddings (placeholder, 384-dim vectors)
- Tracks studios as separate table (allows "all anime by Studio Ghibli" queries)
- Seeds data for Phase 2 (characters, relations tables created but empty for now)

**Output:**
```
✅ Database state:
   Anime: 250
   Studios: 87
   Embeddings: 250
   Characters: 0 (populated in Phase 2)
   Related Anime: 0 (populated in Phase 2)
```

### Step 3: Test Endpoints
```bash
python main.py
# In another terminal:
curl http://localhost:8000/api/stats/overview | jq
```

**Example response:**
```json
{
  "total_anime": 250,
  "average_rating": 7.42,
  "genres_distribution": [
    {"genre": "Action", "count": 128},
    {"genre": "Drama", "count": 95},
    {"genre": "Romance", "count": 67}
  ],
  "studios_distribution": [
    {"studio": "Toei Animation", "count": 12},
    {"studio": "Wit Studio", "count": 8}
  ],
  "top_rated": [
    {"id": 1, "title": "Attack on Titan", "rating": 8.8, ...},
    ...
  ]
}
```

---

## What This Enables for Frontend

With this data model, your frontend can show:

### Home Page:
- Featured anime (top rated)
- Collections (by genre, studio, year)
- Random anime picker

### Dashboard:
- **Genre Chart** — Bar chart of genres (from `stats/by-genre`)
- **Studio Chart** — Top studios ranked (from `stats/overview`)
- **Year Timeline** — Anime releases over time (from `stats/by-year`)
- **Top Rated Table** — Ranked anime (from `stats/overview`)

### Anime Detail Page:
- **Characters Section** — Character cards with images (from `anime/{id}/characters`)
- **Related Anime Section** — Sequels/prequels (from `anime/{id}/related`)
- **Similar Anime** — Same genres/studios (Phase 2: from AI recommendations)

### AI Chat (Phase 2):
- "Show me characters from this anime"
- "What are the sequels to this?"
- "Recommend anime similar to this"

---

## Phase 1 Milestones (Verification Checklist)

✅ **M1.1:** Enhanced fetch script runs
- Command: `python scripts/fetch_anime_enhanced.py`
- Success: Creates `data/anime.json` with 250+ entries including characters, themes, relations

✅ **M1.2:** PostgreSQL schema with 8 tables
- Command: `psql anime_db -c "\dt"`
- Success: Shows `anime`, `studios`, `anime_studios`, `characters`, `anime_characters`, `related_anime`, `embeddings`, `recommendations`

✅ **M1.3:** Data ingested into DB
- Command: `psql anime_db -c "SELECT COUNT(*) FROM anime;"`
- Success: Returns 250 (or close)

✅ **M1.4:** API endpoints return data
- Command: `curl http://localhost:8000/api/stats/overview | jq '.total_anime'`
- Success: Returns 250

---

## Next Steps

### Immediate (Today):
1. Set up PostgreSQL locally (or Docker)
2. Install dependencies: `pip install -r requirements.txt`
3. Run enhanced fetch: `python scripts/fetch_anime_enhanced.py`
4. Run ingest: `python scripts/ingest_anime.py`
5. Test API: `python main.py` + test endpoints
6. Create GitHub repo and commit Phase 1

### Phase 2 (Next 3 days):
- Fetch and populate characters table
- Fetch and populate related_anime table
- Add search/filter endpoints
- Add semantic search
- Add Claude AI recommendation agent
- Add web search integration

### Phase 3 (Week 2):
- React frontend
- Dashboard with charts
- Character showcase
- Related anime section

---

## File Changes Summary

| File | Change |
|------|--------|
| `backend/scripts/fetch_anime_enhanced.py` | ✨ NEW: Fetches characters, themes, relations from AniList |
| `backend/scripts/ingest_anime.py` | 🔄 UPDATED: Enhanced schema with 8 tables |
| `backend/app/routes/characters.py` | ✨ NEW: Character & related anime endpoints |
| `backend/app/routes/stats.py` | ✨ NEW: Dashboard statistics endpoints |
| `backend/main.py` | 🔄 UPDATED: Include new routers |
| `backend/requirements.txt` | ✅ No changes (already has all dependencies) |

---

## Troubleshooting

### "AttributeError: module 'psycopg' has no attribute..."
**Solution:** Install correct version
```bash
pip install --upgrade psycopg[binary]==3.1.12
```

### "pgvector extension not found"
**Solution:** Create it manually
```bash
psql anime_db -c "CREATE EXTENSION vector;"
```

### "Anime characters/relations are empty"
**Expected!** Phase 2 will populate these. For now, schemas are created and ready.

### API returns empty characters list
**Expected!** Characters are fetched in `fetch_anime_enhanced.py` but need to be inserted in Phase 2. The schema is ready.

---

## Ready to Go?

You're set for Phase 1! All you need to do is:

```bash
cd /Users/germanskrylnikov/anime-portal/backend

# 1. Set up environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure database
cp .env.example .env
# Edit .env with your DATABASE_URL

# 3. Fetch data
python scripts/fetch_anime_enhanced.py

# 4. Ingest to DB
python scripts/ingest_anime.py

# 5. Test
python main.py
# In another terminal: curl http://localhost:8000/api/stats/overview | jq

# 6. Commit to git
cd ..
git init
git add .
git commit -m "Phase 1: Enhanced data pipeline with characters & relations support"
git remote add origin https://github.com/germanskrylnikov/anime-portal.git
git push -u origin main
```

Let me know when Phase 1 is complete! 🚀
