# Phase 2: Backend Features & AI Integration

## Overview

**Phase 2 Goal:** Build intelligent backend features that power the dashboard and AI recommendations.

**What you'll have:** 
- ✅ Full-text search + semantic search
- ✅ Claude AI recommendation agent
- ✅ Web search integration for live anime news
- ✅ Smart filtering & sorting
- ✅ Dashboard aggregations

**Timeline:** 3-4 days (parallel development possible)

---

## Architecture

```
Frontend (Coming Phase 3)
      ↓
┌─────────────────────────────────────┐
│       FastAPI Backend (Phase 2)     │
├─────────────────────────────────────┤
│ • Search/Filter Endpoints           │
│ • Semantic Search (pgvector)        │
│ • Claude AI Agent                   │
│ • Web Search Integration            │
│ • Stats/Analytics                   │
└─────────────────────────────────────┘
      ↓
┌─────────────────────────────────────┐
│    PostgreSQL + External APIs       │
├─────────────────────────────────────┤
│ • 250 anime + metadata              │
│ • Vector embeddings                 │
│ • Claude API (recommendations)      │
│ • Web Search (news/info)            │
└─────────────────────────────────────┘
```

---

## Phase 2 Features Breakdown

### 1️⃣ Search & Filter Endpoints

**New Endpoints:**
```
GET /api/anime/search?q=Naruto&genres=Action&year_min=2000&year_max=2024
GET /api/anime/filter?genres=Action,Drama&studios=Studio Ghibli
GET /api/anime/browse?sort=rating&page=1
```

**Milestones:**
- [ ] M2.1: Full-text search on title + plot
- [ ] M2.2: Genre multi-filter
- [ ] M2.3: Year range filter
- [ ] M2.4: Studio filter
- [ ] M2.5: Combine all filters (complex query)

**Implementation (1 day):**
```python
# backend/app/routes/search.py
@router.get("/search")
async def search_anime(
    q: str = Query(...),
    genres: str = Query(None),  # comma-separated
    year_min: int = Query(None),
    year_max: int = Query(None),
    studios: str = Query(None),
    limit: int = Query(20)
):
    # Build dynamic WHERE clauses
    # Search title + plot with ILIKE
    # Filter genres with && (array overlap)
    # Filter year with BETWEEN
```

---

### 2️⃣ Semantic Search (pgvector)

**New Endpoints:**
```
POST /api/anime/semantic-search
{
  "query": "deep story about friendship and overcoming challenges"
}
→ Returns anime ranked by semantic similarity
```

**How it works:**
1. User sends text query → Claude generates embedding
2. PostgreSQL queries pgvector with cosine similarity
3. Returns top-N anime with similar plot embeddings

**Milestones:**
- [ ] M2.6: Generate query embedding (Claude API)
- [ ] M2.7: Cosine similarity search in pgvector
- [ ] M2.8: Rank & return results
- [ ] M2.9: Add explanation why each anime matched

**Implementation (1 day):**
```python
# backend/app/routes/search.py
@router.post("/semantic-search")
async def semantic_search(query: str):
    # 1. Generate embedding from query text
    query_embedding = await generate_embedding(query)
    
    # 2. Search pgvector
    results = await cur.execute("""
        SELECT a.id, a.title, a.plot, 
               1 - (e.plot_embedding <=> %s::vector) as similarity
        FROM embeddings e
        JOIN anime a ON e.anime_id = a.id
        ORDER BY similarity DESC
        LIMIT 10
    """, (query_embedding,))
    
    return results
```

---

### 3️⃣ Claude AI Recommendation Agent

**New Endpoints:**
```
POST /api/recommend
{
  "preferences": "I like dark psychological anime about survival",
  "count": 5
}
→ Returns AI-selected anime with explanations
```

**What Claude does:**
1. Analyzes user preferences
2. Searches anime database (via semantic search)
3. Selects best matches based on themes/genres
4. Returns ranked list with "why we chose this" explanations

**Milestones:**
- [ ] M2.10: Build Claude system prompt (anime expert)
- [ ] M2.11: Create Claude agent function
- [ ] M2.12: Tool calling: search our database
- [ ] M2.13: Tool calling: fetch anime details
- [ ] M2.14: Claude ranks + explains choices

**Implementation (1.5 days):**
```python
# backend/app/routes/recommend.py
from anthropic import Anthropic

client = Anthropic()

tools = [
    {
        "name": "search_anime",
        "description": "Search anime database by themes/genres",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            }
        }
    },
    {
        "name": "get_anime_details",
        "description": "Get full details for an anime by ID",
        "input_schema": {
            "type": "object",
            "properties": {
                "anime_id": {"type": "integer"}
            }
        }
    }
]

@router.post("/recommend")
async def recommend_anime(preferences: str, count: int = 5):
    messages = [
        {
            "role": "user",
            "content": f"Based on these preferences: {preferences}, recommend {count} anime from our database. Use the search_anime tool to find matches, then get_anime_details for each, then rank and explain your choices."
        }
    ]
    
    # Agentic loop
    while True:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            tools=tools,
            messages=messages
        )
        
        if response.stop_reason == "end_turn":
            # Extract recommendations from response
            return parse_recommendations(response)
        
        if response.stop_reason == "tool_use":
            # Handle tool calls, add results to messages
            # Loop continues
            pass
```

---

### 4️⃣ Web Search Integration

**New Endpoint:**
```
GET /api/anime/{id}/news
→ Returns latest news/info about the anime with Claude summary
```

**What it does:**
1. Fetch anime title + year
2. Search web for recent news (Google, Reddit, MAL)
3. Claude summarizes findings
4. Return "What's new with this anime"

**Milestones:**
- [ ] M2.15: Web search integration (SerpAPI or similar)
- [ ] M2.16: Claude summarize search results
- [ ] M2.17: Cache results (avoid duplicate searches)
- [ ] M2.18: Handle no-results gracefully

**Implementation (0.5 days):**
```python
# backend/app/routes/recommend.py
@router.get("/anime/{anime_id}/news")
async def get_anime_news(anime_id: int):
    anime = await get_anime(anime_id)
    
    # Search web
    search_results = await web_search(f"{anime.title} {anime.year} news")
    
    # Summarize with Claude
    summary = await client.messages.create(
        model="claude-3-5-sonnet-20241022",
        messages=[{
            "role": "user",
            "content": f"Summarize this news about {anime.title}:\n{search_results}"
        }]
    )
    
    return {
        "anime_title": anime.title,
        "summary": summary.content[0].text,
        "sources": search_results
    }
```

---

### 5️⃣ Enhanced Dashboard Stats

**Improvements:**
```
GET /api/stats/trending?season=FALL_2024
GET /api/stats/similar-to/{anime_id}
GET /api/stats/genre-breakdown?genre=Action
```

**What's new:**
- Seasonal trending (top anime per season)
- Similar anime (based on shared genres/studios)
- Deep genre analytics

**Milestones:**
- [ ] M2.19: Seasonal rankings
- [ ] M2.20: Similar anime algorithm
- [ ] M2.21: Genre deep-dive stats

---

## Implementation Strategy

### Day 1: Search & Filtering
1. Create `backend/app/routes/search.py`
2. Implement full-text search (ILIKE)
3. Implement genre/year/studio filters
4. Test with curl

### Day 2: Semantic Search + Claude Prep
1. Create embedding generation function
2. Implement pgvector similarity search
3. Set up Claude API client
4. Test embedding search

### Day 3: Claude AI Agent
1. Build recommendation agent with tools
2. Test tool calling (search_anime, get_anime_details)
3. Implement ranking logic
4. Add explanations to recommendations

### Day 4: Web Search + Polish
1. Integrate web search (optional: SerpAPI free tier)
2. Add Claude news summarization
3. Implement caching
4. Full integration testing

---

## Testing Phase 2

### Search Tests
```bash
# Full-text search
curl 'http://localhost:8000/api/anime/search?q=Nar' | jq '.[] | .title'

# Filter by genre
curl 'http://localhost:8000/api/anime/filter?genres=Action,Drama' | jq '.[] | {title, genres}'

# Year range
curl 'http://localhost:8000/api/anime/search?q=&year_min=2020&year_max=2024' | jq '.[] | {title, year}'
```

### Semantic Search Tests
```bash
curl -X POST http://localhost:8000/api/anime/semantic-search \
  -H "Content-Type: application/json" \
  -d '{"query": "sad romance about time travel"}' | jq '.[] | {title, rating, similarity}'
```

### AI Recommendation Tests
```bash
curl -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"preferences": "dark psychological thriller about survival"}' | jq
```

### Web Search Tests
```bash
curl 'http://localhost:8000/api/anime/1/news' | jq '.summary'
```

---

## Key Decisions & Trade-offs

| Decision | Choice | Why |
|----------|--------|-----|
| **Search method** | Full-text + Semantic | Covers both exact matches and vibe searches |
| **AI model** | Claude 3.5 Sonnet | Best quality, reasonable cost, tool calling support |
| **Web search** | Optional (SerpAPI free tier) | Nice-to-have, not critical for portfolio |
| **Caching** | Redis (optional) | Can add later if needed, skip for now |
| **Rate limiting** | Simple counter | Prevent abuse, can upgrade later |

---

## Deliverables (End of Phase 2)

✅ 8 new API endpoints  
✅ Claude AI recommendation agent  
✅ Web search integration (optional)  
✅ Full-text + semantic search  
✅ All endpoints tested & working  
✅ Committed to GitHub  

**Ready for Phase 3:** Frontend can consume all these APIs

---

## Success Criteria

**Phase 2 is complete when:**

1. ✅ `GET /api/anime/search?q=...` works with filters
2. ✅ `POST /api/anime/semantic-search` returns ranked results
3. ✅ `POST /api/recommend` returns Claude-ranked anime with explanations
4. ✅ `GET /api/anime/{id}/news` returns summary (optional)
5. ✅ All endpoints tested with real data
6. ✅ Code committed & pushed to GitHub

---

## Files to Create/Modify

**New files:**
- `backend/app/routes/search.py` — Search & filter
- `backend/app/routes/recommend.py` — AI recommendations & web search
- `backend/app/utils/embeddings.py` — Embedding generation (Claude)
- `backend/app/utils/claude_agent.py` — Claude agent setup

**Modify:**
- `backend/main.py` — Add new routers
- `backend/requirements.txt` — Add any new dependencies

---

## Start Phase 2?

**Ready to go?** I'll create:
1. Search route skeleton
2. Semantic search implementation
3. Claude agent setup
4. Web search integration (optional)

All with clear milestones to verify before moving to Phase 3.

Let me know! 🚀
