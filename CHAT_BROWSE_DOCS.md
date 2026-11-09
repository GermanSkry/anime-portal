# Anime Portal: Chat & Browse Documentation

## 💬 AI Chat System

### Architecture Flow

```
User Message
    ↓
Frontend (Chat.jsx / ChatModal.jsx)
    ├─ Build message history (with summarization if >5 messages)
    └─ Send to backend
    ↓
Backend (FastAPI chat endpoint)
    ├─ Extract anime references from Claude's response
    ├─ Store in PostgreSQL (user_ip, message, response, anime_references)
    └─ Return response + anime IDs
    ↓
Frontend renders response
    ├─ MessageRenderer: Parse **Title** → convert to clickable links
    └─ Store in animeReferences for next turn
```

### Key Features

#### ✅ Chat Continuation
Previous messages are automatically sent to Claude in each request. Claude maintains conversation context across multiple turns without any manual history management.

#### ✅ Message Summarization
When conversations exceed 5 messages, older messages are automatically summarized into `[Earlier conversation summary]` to save tokens while maintaining context. Only the last 5 messages stay full.

#### ✅ Database-First Search
Claude receives database results for anime queries. The backend extracts genre/title/plot keywords from user messages and searches PostgreSQL before responding, reducing reliance on web search and saving API quota.

#### ✅ Anime Link Extraction
Claude formats recommendations as `**Title**`. Backend extracts these titles, finds matching anime IDs in database, and stores them. Frontend converts to clickable links pointing to `/title/{id}`.

#### ✅ History Isolation
Title page chat shows only conversations about that specific anime (filtered by `anime_context_id`). General Chat page shows all context-free conversations. Each anime has its own isolated history.

#### ✅ Custom Greetings
Title page shows personalized, randomized greetings that include title, year, genres, and rating. Each load picks a different greeting for better UX.

### Message Flow Example

| Step | Component | Action |
|------|-----------|--------|
| 1 | Frontend | User types "recommend action anime" |
| 2 | Frontend | Builds `messageHistory` with summarization if needed |
| 3 | Backend | Receives message + history, calls Claude API with full context |
| 4 | Backend | Claude returns: "Here are top action anime: **Demon Slayer** - ..." |
| 5 | Backend | Extracts "Demon Slayer", finds in DB, returns anime_references array |
| 6 | Frontend | MessageRenderer converts "**Demon Slayer**" to clickable link |
| 7 | Backend | Saves chat to DB: (user_ip, message, response, anime_references) |

---

## 🔍 Browse & Search System

### Architecture: Backend Search

```
User types in search bar
    ↓
Frontend (Browse.jsx)
    └─ Send query to backend → /api/search/anime?q=gate
    ↓
Backend (FastAPI search endpoint)
    ├─ Fuzzy search on title, genres, studio, year
    ├─ Score and rank results by relevance
    └─ Return JSON array of matching anime
    ↓
Frontend renders results
    └─ Displays search results in Browse grid
```

### Why Backend Search?

**Advantages:**
- ✅ **Scales to large DB** - Can handle 1M+ anime without client-side load
- ✅ **Database-backed** - Complex queries, indexing, aggregations
- ✅ **Extensible** - Easy to add filters (rating range, year range, multiple genres)
- ✅ **Cacheable** - Server can cache popular searches
- ✅ **Secure** - Validation/sanitization on backend
- ✅ **Future-proof** - Ready for growth

**Current approach:**
- All search logic lives on backend (`/api/search/anime?q=query&limit=10`)
- Frontend just sends query and renders results

### Search Endpoint

**Request:**
```
GET /api/search/anime?q=gate&limit=10
```

**Response:**
```json
[
  {
    "id": 123,
    "title_english": "Steins;Gate",
    "title": "シュタインズゲート",
    "rating": 9.1,
    "year": 2011,
    "genres": ["Sci-Fi", "Thriller"],
    "cover_image": "...",
    "relevance_score": 95
  },
  ...
]
```

### Fuzzy Search Algorithm (Backend)

Search doesn't require exact matches. Type "gate" → finds "Steins;Gate"

| Match Type | Score | Example |
|-----------|-------|---------|
| Exact match | 100 | "Jujutsu Kaisen" = "Jujutsu Kaisen" |
| Starts with | 80 | "Juju" → "Jujutsu Kaisen" |
| Word boundary | 75 | "gate" → "Steins;Gate" |
| Substring match | 60 | "demon" → "Demon Slayer" |
| Fuzzy sequence | 40-50 | "sga" → "Steins;Gate" (chars in order) |

### Browse Page Sections

| Section | Sorting | Count |
|---------|---------|-------|
| ⭐ Best (Highest Rated) | Rating descending | 4 anime |
| 🆕 New (Recent) | Year descending | 4 anime |
| ⚔️ Action | Genre filter + rating | 4 anime |
| 🎭 Drama | Genre filter + rating | 4 anime |
| 🧠 Psychological | Genre filter + rating | 4 anime |

### Search Features

#### ✅ Auto-search as you type
No need to click Search button. Start typing and results appear via backend calls. Type "ston" → see "Dr. Stone" with results from server.

#### ✅ Clear returns to default
Delete all text from search bar → instantly see original Browse layout (Best, New, Action, Drama, Psychological sections).

#### ✅ Relevance sorting
Results sorted by relevance score from backend. Perfect match appears first, fuzzy matches last. Genre and year queries also scored.

---

## 🔗 Integration: Chat → Browse

Chat and Browse work together seamlessly:

1. **Chat recommends anime** → Anime names become clickable links
2. **Click link** → Navigate to Title page
3. **Title page has chat modal** → Open contextual chat about that anime
4. **Chat history is isolated** → Only see conversations about this anime
5. **Browse page has search** → Find anime by title/genre before chatting

---

## ⚙️ Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React 18 + Vite | Chat UI, Browse, MessageRenderer, search UI |
| Backend | FastAPI (Python) | Chat endpoint, search endpoint, history storage |
| AI | Claude via OpenRouter | Conversational AI, recommendations |
| Database | PostgreSQL | Anime data, chat history, anime_references JSONB |
| Search (optional) | Go microservice | Parallel web search + semantic search |

---

## 📝 Database Schema

### chat_history table
```sql
CREATE TABLE chat_history (
  id SERIAL PRIMARY KEY,
  user_ip VARCHAR(45),
  user_message TEXT,
  assistant_response TEXT,
  anime_context_id INTEGER,
  anime_references JSONB,  -- [{title, id}, ...]
  created_at TIMESTAMP DEFAULT NOW()
);
```

### anime table (relevant columns)
```sql
CREATE TABLE anime (
  id SERIAL PRIMARY KEY,
  title VARCHAR(255),
  title_english VARCHAR(255),
  rating FLOAT,
  year INTEGER,
  genres TEXT[],
  studio VARCHAR(255),
  plot TEXT,
  cover_image VARCHAR(500),
  ...
);
```

---

## 🚀 Future Scaling

### When to optimize:
- **>1,000 anime** - Add full-text search indices on PostgreSQL
- **>10,000 anime** - Consider Elasticsearch for advanced search
- **>100,000 anime** - Add Redis caching for popular searches
- **Multiple regions** - Cache search results geographically

### Current approach is ready for:
- Up to ~100K anime with basic indexing
- Complex filtering (multiple genres, rating ranges, year ranges)
- Real-time search feedback
- Advanced relevance ranking

---

## 📋 Summary

The Anime Portal combines:

- **Smart Chat** - Context-aware, summarizes long conversations, finds anime in database
- **Scalable Search** - Backend-powered fuzzy matching, ready for large DB growth
- **Isolated History** - Each anime has its own chat context, general chat is separate
- **Seamless UX** - Chat → Search → Title → Chat again, all integrated
- **Future-proof** - Designed to scale from 100 to 100K+ anime

