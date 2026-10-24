# Anime Portal: Complete Roadmap

## Current Status: Phase 2 ✅ COMPLETE

**What we have:**
- 250 anime in PostgreSQL with vectors
- Full-text search endpoint
- Semantic search endpoint  
- AI recommendations endpoint
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

## Phase 3: Frontend (Chat UI) 🎨

### Goal
Build React interface for the chatbot

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

3. **Search Suggestions**
   - Quick buttons ("Action", "Dark", "Recently Trending")
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
│   │   └── AnimeDetail.tsx
│   ├── pages/
│   │   ├── ChatPage.tsx
│   │   └── AnimePage.tsx
│   ├── hooks/
│   │   ├── useChat.ts
│   │   └── useAnime.ts
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

## After Phase 3: Deployment 🚀

- Frontend: Vercel (auto-deploy from main)
- Backend: Railway or Heroku
- Database: Managed PostgreSQL
- Web search: SerpAPI credits ($10/month)

---

## Key URLs When Done

- **App:** `https://anime-portal.vercel.app`
- **API:** `https://anime-api.railway.app`
- **GitHub:** Already public for portfolio

This is portfolio gold. 🎯
