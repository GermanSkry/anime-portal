# Phase 1: Data Pipeline Setup

## Prerequisites

Before starting, make sure you have:
- Python 3.10+ installed
- PostgreSQL installed locally (or Docker)
- Git installed

## Step 1: Create Virtual Environment

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

## Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 3: Set Up Database

### Option A: Local PostgreSQL (Recommended for development)

```bash
# Create database
createdb anime_db

# Set up .env file
cp .env.example .env

# Edit .env and set:
# DATABASE_URL=postgres://postgres:password@localhost:5432/anime_db
# (Replace 'postgres' and 'password' with your actual credentials)
```

### Option B: Docker PostgreSQL

```bash
docker run --name postgres-anime \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=anime_db \
  -p 5432:5432 \
  -d postgres:latest

# Then set .env to:
# DATABASE_URL=postgres://postgres:password@localhost:5432/anime_db
```

## Step 4: Verify Database Connection

```bash
# Test connection
python -c "
import asyncio
import psycopg
from app.config import settings

async def test():
    conn = await psycopg.AsyncConnection.connect(settings.database_url)
    async with conn.cursor() as cur:
        await cur.execute('SELECT 1')
        result = await cur.fetchone()
    await conn.close()
    print('✓ Database connected!')

asyncio.run(test())
"
```

## Step 5: Fetch Anime Data (Enhanced with Characters & Relations)

This downloads 250 anime from AniList API with characters, themes, and related anime (~60 seconds):

```bash
python scripts/fetch_anime_enhanced.py
```

**Expected output:**
```
🔄 Fetching enhanced anime data from AniList (with characters & relations)...

Fetching page 1...
  Fetched 50 anime
Fetching page 2...
  Fetched 50 anime
...

✅ Data saved:
   Anime: /path/to/backend/data/anime.json (250 entries)
   Characters: 1,847 unique characters
   Relations: 342 anime relationships

📊 Statistics:
   Total character mentions: 2,150
   Avg characters per anime: 8.6
   Avg themes per anime: 3.2
```

**Verify:**
```bash
# Check data was saved
wc -l data/anime.json  # Should show ~2500 lines
jq '.[0] | keys' data/anime.json  # Should show all fields
```

## Step 6: Ingest Data into Database

```bash
python scripts/ingest_anime.py
```

**Expected output:**
```
🚀 Starting data ingestion (Phase 1+2 schema)...

📥 Loading anime from /path/to/backend/data/anime.json...
   Loaded 250 anime
🔧 Initializing database schema...
📑 Creating indexes...
🗑️  Clearing old data...
📝 Inserting anime...
  Processed 50/250
  Processed 100/250
  Processed 150/250
  Processed 200/250
  Processed 250/250
✓ Inserted 250 anime with enhanced schema

✅ Database state:
   Anime: 250
   Studios: 87
   Embeddings: 250
   Characters: 0 (will add in Phase 2)
   Related Anime: 0 (will add in Phase 2)

✅ Done!
```

**Verify:**
```bash
# Check data in database
psql anime_db -c "SELECT COUNT(*) FROM anime;"  # Should be 250
psql anime_db -c "SELECT title, rating FROM anime LIMIT 5;"
```

## Step 7: Test API Endpoints

```bash
# Start server
python main.py
```

**In another terminal, test these endpoints:**

```bash
# Health check
curl http://localhost:8000/health

# List anime
curl http://localhost:8000/api/anime?limit=5

# Get single anime
curl http://localhost:8000/api/anime/1

# Get characters in anime (Phase 2, will be empty for now)
curl http://localhost:8000/api/anime/1/characters

# Get related anime - sequels, prequels (Phase 2, will be empty for now)
curl http://localhost:8000/api/anime/1/related

# Dashboard stats
curl http://localhost:8000/api/stats/overview

# Genre distribution
curl http://localhost:8000/api/stats/by-genre | jq '.[] | select(.genre == "Action")'

# Anime by year
curl http://localhost:8000/api/stats/by-year?limit=10
```

**Expected response from `/api/anime?limit=5`:**
```json
[
  {
    "id": 1,
    "title": "Attack on Titan",
    "title_english": "Attack on Titan",
    "year": 2013,
    "rating": 8.8,
    "genres": ["Action", "Dark", "Drama"],
    "studios": ["Wit Studio"],
    "cover_image": "https://..."
  },
  ...
]
```

---

## Phase 1 Milestones (Verification Checklist)

- [ ] **M1.1:** `python scripts/fetch_anime.py` runs successfully, creates `data/anime.json` with 250+ titles
  - Check: `wc -l data/anime.json` shows ~2500 lines; `jq '.[0] | .title' data/anime.json` shows a title

- [ ] **M1.2:** PostgreSQL schema created with `anime` and `embeddings` tables
  - Check: `psql anime_db -c "\dt"` shows both tables; `\d anime` shows all columns

- [ ] **M1.3:** Data ingested (250 anime + embeddings)
  - Check: `SELECT COUNT(*) FROM anime;` returns 250; `SELECT COUNT(*) FROM embeddings;` returns 250

- [ ] **M1.4:** FastAPI endpoints return data
  - Check: `curl http://localhost:8000/api/anime?limit=1` returns valid JSON with title, rating, genres

---

## Troubleshooting

### Database connection fails
```
Error: psycopg.OperationalError: could not connect to server
```
**Solution:**
- Verify PostgreSQL is running: `psql postgres -c "SELECT 1"`
- Check DATABASE_URL in `.env` is correct
- Verify username/password match your PostgreSQL credentials

### Script hangs at fetch
**Solution:**
- AniList API might be slow. It's normal to take 30-60 seconds.
- If it times out, run again.

### Port 8000 already in use
```
OSError: [Errno 48] Address already in use
```
**Solution:**
```bash
# Use different port
PORT=8001 python main.py
# Or find and kill the process
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

### Embeddings insertion fails
**Solution:**
- Ensure PostgreSQL extension installed: `psql anime_db -c "CREATE EXTENSION vector;"`
- Or install pgvector: `pip install pgvector`

---

## Next Steps

Once Phase 1 is complete and all milestones verified:

1. **Commit to git:**
```bash
cd /Users/germanskrylnikov/anime-portal
git init
git add .
git commit -m "Phase 1: Data pipeline setup"
git remote add origin https://github.com/germanskrylnikov/anime-portal.git
git branch -M main
git push -u origin main
```

2. **Phase 2 (Backend):** Build additional endpoints
   - Search/filter
   - Semantic search
   - Stats/aggregations
   - Claude AI recommendations

Ready? Let me know when Phase 1 milestones are verified! 🚀
