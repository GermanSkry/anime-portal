# Anime Portal: Complete Roadmap

## Current Status: Phase 4 ✅ COMPLETE

**What we have:**
- 250 anime in PostgreSQL with vectors
- Full-text search + semantic search endpoints
- AI recommendations endpoint
- **Smart chat with database-first + SerpAPI web search** ⭐
- Real-time trending anime info
- All tested and working

---

## Phase 4: Chatbot + Web Search (NEXT) 💬

### Goal
Build a Claude-powered chatbot that:
- Answers questions about anime
- Searches our database
- Searches the web for live info (news, reviews, trending)
- Provides context + sources

### Endpoints to Create

**1. Chat Endpoint**
```
POST /api/chat
{
  "message": "What's a good action anime right now?",
  "history": [...]  // optional conversation history
}

Response:
{
  "response": "I'd recommend...",
  "sources": ["https://...", ...],
  "anime_ids": [1, 2, 3]
}
```

### Architecture

```
User Message
    ↓
Claude Agent (via OpenRouter)
    ├── Tool 1: Search anime DB
    │   └── Find matching anime (title, genre, rating)
    ├── Tool 2: Search web
    │   └── Find news, reviews, trending
    └── Combine results → natural response
    ↓
Return answer + sources + anime IDs
```

### Implementation Details

**Web Search Service:**
- Option 1: SerpAPI (free tier: 100 queries/month)
- Option 2: DuckDuckGo (free, no rate limit)
- Option 3: Custom scraper (more complex)
- **Decision: SerpAPI for reliability**

**Claude Tools:**
```python
tools = [
    {
        "name": "search_anime_db",
        "description": "Search our database for anime",
        "input_schema": {...}
    },
    {
        "name": "search_web",
        "description": "Search web for anime news/reviews",
        "input_schema": {...}
    }
]
```

**Files to Create:**
- `backend/app/routes/chat.py` — Chat endpoint
- `backend/app/utils/web_search.py` — Web search integration
- `backend/app/utils/claude_agent.py` — Claude agent setup
- `backend/app/utils/chat_memory.py` — Conversation history (optional)

**Files to Modify:**
- `backend/main.py` — Add chat router
- `backend/requirements.txt` — Add requests or httpx (for web search)
- `backend/.env.example` — Add SERPAPI_KEY

### Testing

```bash
# Basic chat
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message":"recommend dark anime with web search"}'

# With history
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message":"tell me more",
    "history":[
      {"role":"user","content":"recommend action"},
      {"role":"assistant","content":"..."}
    ]
  }'
```

### Success Criteria

✅ Chat endpoint working  
✅ Claude searches anime DB  
✅ Web search returns results  
✅ Responses include sources  
✅ Conversation history preserved  
✅ Multiple turns work smoothly

---

## Phase 5: Go Microservice + Caching + Monitoring 🚀 (3-4 days)

### Goal
Production-ready Go microservice with caching, monitoring, and error tracking

### What to Build

**Part A: Go Microservice (2-3 days)**
```
go-search/
├── main.go                (service entry)
├── handlers/search.go     (API endpoints)
├── cache/redis.go         (NEW - caching layer)
├── db/history.go          (NEW - search history)
├── monitoring/sentry.go   (NEW - error tracking)
├── docker-compose.yml
├── Dockerfile
└── go.mod
```

**Part B: Monitoring (1 day)**
- Sentry: Capture backend errors (Python + Go)
- PostHog: Track user events + analytics
- Structured logging
- Performance metrics

### Features

**1. Redis Caching Layer**
```
Query → Check Cache → 
  ✅ Found? Return cached (instant)
  ❌ Miss? Call SerpAPI → Cache → Return

Result: Save 60-70% SerpAPI quota!
```

**2. Search History**
```
Log: {query, results, timestamp, api_calls}
Benefits:
- Analytics dashboard
- Avoid duplicate searches
- Track user behavior
- Trending queries detection
```

**3. Error Tracking (Sentry)**
```
❌ Exception in search?
   → Sentry captures automatically
   → Alert on dashboard
   → Error grouping + trends
```

**4. Analytics (PostHog)**
```
- User search behavior
- API performance
- Cache hit rates
- Feature usage tracking
```

### Why This is Professional
- ✅ Production-ready architecture
- ✅ Shows DevOps maturity
- ✅ Error handling culture
- ✅ Data-driven optimization
- ✅ Monitoring from day 1

---

## Phase 3: Frontend (Chat UI) 🎨 (AFTER Phase 5)

### Goal
Build React interface for the chatbot with PostHog tracking

### Add Monitoring to Frontend
- PostHog events: chat sent, search performed, recommendations clicked
- Performance metrics: response times
- User behavior tracking
- Funnel analysis

### Features

1. **Chat Interface**
   - Message input
   - Message history display
   - Streaming responses
   - Loading states

2. **Anime Results**
   - Inline anime cards in chat
   - Links to details
   - Images, ratings, genres

3. **Search & Filter Dashboard**
   - Full-text search bar
   - Multi-filter panel:
     - Genre checkboxes
     - Year range slider
     - Studio filter
     - Rating sort (high → low)
   - Quick preset buttons ("Action", "Dark", "Recently Trending")
   - Previous searches

4. **Details Page**
   - Full anime info
   - Trailer (YouTube embed)
   - Cast/Studios
   - Links to external sites

### Tech Stack
- React 18 + TypeScript
- Tailwind CSS
- Zustand (state management)
- React Query (API calls)

### File Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── ChatWindow.tsx
│   │   ├── MessageBubble.tsx
│   │   ├── AnimeCard.tsx
│   │   ├── AnimeDetail.tsx
│   │   └── SearchFilters.tsx (genres, year, studio, rating)
│   ├── pages/
│   │   ├── ChatPage.tsx
│   │   ├── BrowsePage.tsx (dashboard with filters)
│   │   └── AnimePage.tsx
│   ├── hooks/
│   │   ├── useChat.ts
│   │   ├── useAnime.ts
│   │   └── useSearch.ts (filter state)
│   └── App.tsx
```

### Success Criteria

✅ Chat UI responsive  
✅ Messages display correctly  
✅ Anime cards render  
✅ Details page works  
✅ Mobile-friendly  
✅ Streaming responses feel natural

---

## Why Phase 4 → Phase 3?

| Aspect | Phase 4 First | Phase 3 First |
|--------|---|---|
| **Backend complete** | ✅ Yes | ❌ Missing web search |
| **UI changes needed** | ❌ No | ✅ Might rebuild for chat |
| **Time to impressive** | Slower | Faster initially, then rebuild |
| **Quality** | Higher (all features ready) | Lower (incomplete backend) |

**Winner: Phase 4 → Phase 3** — All backend done before touching UI

---

## Timeline Estimate

- **Phase 4:** 2-3 days (web search + agent setup + testing)
- **Phase 3:** 3-4 days (React UI + polish)
- **Total:** ~1 week for fully functional app

---


## Phase 6: Deployment + Monitoring 🌍

### Deploy Services
- **Frontend:** Vercel (auto-deploy from main)
- **Backend:** Railway (Python FastAPI)
- **Go Service:** Railway (microservice)
- **Database:** PostgreSQL managed
- **Cache:** Redis (in-memory cache)
- **Web Search:** SerpAPI ($0 free tier)

### Monitoring Live
- **Sentry:** Error tracking + alerts
  - Capture exceptions from Python + Go
  - Performance monitoring
  - Deployment tracking
  
- **PostHog:** User analytics
  - User behavior funnels
  - Feature usage metrics
  - Event tracking
  - Session recording (optional)

### Dashboards
- Sentry: Error trends, performance
- PostHog: User analytics, engagement
- Railway: Service health, logs
- Redis: Cache hit rates, memory usage

---

## Timeline (Optimized Order)

- **Phase 4 (Chat + Web Search):** ✅ COMPLETE
- **Phase 5 (Go + Caching + Monitoring):** ⏳ NEXT - 3-4 days
  - Go microservice (2-3 days)
  - Redis caching (save 60-70% quota)
  - Sentry + PostHog (monitoring)
  - Production-ready backend
- **Phase 3 (React UI):** AFTER Phase 5 - 3-4 days
  - Build on fully optimized backend
  - PostHog tracking in frontend
  - No backend changes needed
- **Phase 6 (Deploy + Monitor):** FINAL - 1 day
  - Railway (Python + Go)
  - Vercel (React)
  - Sentry + PostHog dashboards live

---

## Portfolio Impact

### What You'll Show

✅ **Phase 1-4:** Full-stack AI application  
✅ **Phase 5:** Production-ready backend with monitoring  
✅ **Phase 6:** Professional DevOps + observability  

### Impressive Skills on Display

**Backend:**
- FastAPI (Python) + Go microservices
- PostgreSQL with pgvector (AI embeddings)
- Redis caching layer
- Docker orchestration
- API design patterns

**Frontend:**
- React 18 + TypeScript
- Real-time chat UI
- Performance optimization
- Analytics integration

**AI/ML:**
- Claude API integration
- Web search (SerpAPI)
- Semantic search with embeddings
- Recommendation system

**DevOps/Monitoring:**
- Docker + docker-compose
- Multi-service orchestration
- Sentry error tracking
- PostHog analytics
- Production deployment
- Monitoring dashboards

**This is professional portfolio gold.** 🎯

Recruiters will see:
- Full-stack capability ✅
- Production-mindset (monitoring from day 1) ✅
- Multi-language backend ✅
- AI integration experience ✅
- DevOps maturity ✅
