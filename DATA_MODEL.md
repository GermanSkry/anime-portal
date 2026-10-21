# Data Model & Schema Design

## Current Anime Fields (From AniList)

```json
{
  "id": 1,                           // Unique AniList ID
  "title": "Attack on Titan",        // Main title
  "title_english": "Attack on Titan", // English title
  "year": 2013,                      // Release year
  "rating": 8.8,                     // AniList score (0-10)
  "plot": "In a world...",           // Synopsis/description
  "cover_image": "https://...",      // Cover art URL
  "genres": ["Action", "Dark"],      // Genre tags
  "studios": ["Wit Studio"]          // Production studios
}
```

---

## Enhanced Data Model (Recommended)

### Why Enrich Data?

Your current model is good for MVP, but lacks:
- ❌ User engagement metrics (no sense of "how popular")
- ❌ Content details (no characters, VA, opening themes)
- ❌ Relationships (no sequels, prequels, spin-offs)
- ❌ Time-based data (no trends, seasonal info)
- ❌ Detailed reviews/ratings

**With enriched data, your dashboard becomes much more interesting:**
- "Top trending anime this season"
- "Characters in this anime"
- "Similar anime" (based on shared genres/studios)
- "Watch trends over time"
- "Staff (directors, VAs)"

---

## Proposed Data Sources

### Primary: AniList API (Already using)
✅ Excellent for: Anime metadata, genres, studios, score, character names  
⚠️ Limited for: User engagement, reviews, trends

### Secondary: MyAnimeList (MAL)
✅ Has: Different scoring system (shows alternative popularity), user count, ranked position  
✅ Use for: Cross-validation, user engagement metrics  
⏱️ Rate limit: Slower, but doable

### Tertiary: TMDB/IMDB (Optional)
✅ Has: External ratings, IMDb scores, more detailed cast info  
⚠️ Complex: Not all anime are on these platforms

### Quaternary: Community Data (Advanced)
✅ Has: Reddit discussions, seasonal rankings, trending metrics  
⚠️ Slow: Requires scraping/API calls

---

## Recommended Schema (PostgreSQL)

### Core Tables

#### 1. **anime** (Main table)
```sql
CREATE TABLE anime (
  -- Primary key & IDs
  id SERIAL PRIMARY KEY,
  anilist_id INTEGER UNIQUE NOT NULL,
  mal_id INTEGER UNIQUE,                    -- MyAnimeList ID (optional)
  
  -- Titles
  title VARCHAR(255) NOT NULL,
  title_english VARCHAR(255),
  title_japanese VARCHAR(255),              -- NEW: Original Japanese title
  
  -- Metadata
  year INTEGER,
  season VARCHAR(20),                       -- NEW: "WINTER_2013", "SPRING_2023"
  episodes INTEGER,                         -- NEW: Episode count
  status VARCHAR(50),                       -- NEW: "FINISHED", "AIRING", "NOT_YET_AIRED"
  
  -- Descriptions & media
  plot TEXT,
  cover_image VARCHAR(255),
  banner_image VARCHAR(255),                -- NEW: Wide banner for hero
  
  -- Ratings & engagement
  anilist_score FLOAT,                      -- 0-10
  anilist_popularity INTEGER,               -- Number of users who've interacted
  mal_score FLOAT,                          -- NEW: MyAnimeList score (optional)
  
  -- Arrays (PostgreSQL native)
  genres TEXT[] DEFAULT '{}',
  themes TEXT[] DEFAULT '{}',               -- NEW: "School", "Magic", "Romance"
  content_warnings TEXT[] DEFAULT '{}',     -- NEW: "Violence", "Gore"
  
  -- Relationships (foreign keys)
  -- studios: separate table (many-to-many)
  -- characters: separate table
  -- related_anime: separate table
  
  -- Timestamps
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast queries
CREATE INDEX idx_anime_year ON anime(year);
CREATE INDEX idx_anime_season ON anime(season);
CREATE INDEX idx_anime_rating ON anime(anilist_score DESC);
CREATE INDEX idx_anime_popularity ON anime(anilist_popularity DESC);
CREATE INDEX idx_anime_genres ON anime USING GIN(genres);
```

#### 2. **studios** (Many-to-many relationship)
```sql
CREATE TABLE studios (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) UNIQUE NOT NULL,
  country VARCHAR(100),                     -- "Japan", "South Korea"
  founded_year INTEGER,
  website VARCHAR(255)
);

CREATE TABLE anime_studios (
  anime_id INTEGER REFERENCES anime(id) ON DELETE CASCADE,
  studio_id INTEGER REFERENCES studios(id) ON DELETE CASCADE,
  role VARCHAR(50) DEFAULT 'Animation',     -- "Animation", "Production"
  PRIMARY KEY (anime_id, studio_id)
);
```

#### 3. **characters** (NEW: Characters in anime)
```sql
CREATE TABLE characters (
  id SERIAL PRIMARY KEY,
  anilist_char_id INTEGER UNIQUE,
  name VARCHAR(255) NOT NULL,
  name_japanese VARCHAR(255),
  role VARCHAR(100),                        -- "MAIN", "SUPPORTING"
  description TEXT,
  image_url VARCHAR(255),
  voice_actors TEXT[],                      -- Simple array for now
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE anime_characters (
  anime_id INTEGER REFERENCES anime(id) ON DELETE CASCADE,
  character_id INTEGER REFERENCES characters(id) ON DELETE CASCADE,
  role_type VARCHAR(50),                    -- "MAIN", "SUPPORTING"
  PRIMARY KEY (anime_id, character_id)
);
```

#### 4. **related_anime** (NEW: Sequels, prequels, spin-offs)
```sql
CREATE TABLE related_anime (
  id SERIAL PRIMARY KEY,
  anime_id_from INTEGER REFERENCES anime(id) ON DELETE CASCADE,
  anime_id_to INTEGER REFERENCES anime(id) ON DELETE CASCADE,
  relationship_type VARCHAR(50),            -- "SEQUEL", "PREQUEL", "SPIN_OFF", "SIDE_STORY"
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for graph traversal
CREATE INDEX idx_related_from ON related_anime(anime_id_from);
CREATE INDEX idx_related_to ON related_anime(anime_id_to);
```

#### 5. **embeddings** (For semantic search)
```sql
CREATE TABLE embeddings (
  id SERIAL PRIMARY KEY,
  anime_id INTEGER UNIQUE REFERENCES anime(id) ON DELETE CASCADE,
  plot_embedding vector(384),               -- From plot description
  theme_embedding vector(384),              -- NEW: From themes + genres (optional)
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 6. **recommendations** (NEW: Community recommendations)
```sql
CREATE TABLE recommendations (
  id SERIAL PRIMARY KEY,
  anime_id INTEGER REFERENCES anime(id) ON DELETE CASCADE,
  recommended_anime_id INTEGER REFERENCES anime(id) ON DELETE CASCADE,
  score FLOAT,                              -- How often recommended together (0-1)
  reason VARCHAR(255),                      -- "Similar genre", "Same studio"
  source VARCHAR(100) DEFAULT 'content',    -- "content", "user", "trending"
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_recommendations ON recommendations(anime_id, score DESC);
```

#### 7. **seasonal_trends** (NEW: Time-series data)
```sql
CREATE TABLE seasonal_trends (
  id SERIAL PRIMARY KEY,
  anime_id INTEGER REFERENCES anime(id) ON DELETE CASCADE,
  season VARCHAR(20),                       -- "WINTER_2023", "SPRING_2024"
  rank_position INTEGER,                    -- Rank in that season
  views_estimate INTEGER,                   -- Estimated views (from comments, posts)
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_seasonal_trends ON seasonal_trends(season, rank_position);
```

---

## Data Model Diagram

```
┌─────────────────────────────────────────────────────┐
│                      anime                          │
│  (id, anilist_id, title, year, season, episodes,   │
│   plot, score, popularity, genres[], themes[], ...) │
└──────────────┬──────────────────────────────────────┘
               │
        ┌──────┼──────┐
        │      │      │
        ▼      ▼      ▼
   ┌────────────────┐  ┌──────────────────┐  ┌──────────────┐
   │anime_studios   │  │ anime_characters │  │embeddings    │
   ├────────────────┤  ├──────────────────┤  ├──────────────┤
   │ anime_id       │  │ anime_id         │  │ anime_id     │
   │ studio_id ────┼─→│ character_id ────┼─→│ plot_emb[384]│
   │ role           │  │ role_type        │  │ theme_emb[]  │
   └────────────────┘  └──────────────────┘  └──────────────┘
        │                      │
        ▼                      ▼
    ┌────────────┐      ┌───────────────┐
    │ studios    │      │ characters    │
    │(id, name)  │      │(id, name, VA) │
    └────────────┘      └───────────────┘

┌──────────────────────────────────────────────────────┐
│            related_anime (graph)                     │
│  anime_id_from → anime_id_to (SEQUEL, PREQUEL, ...) │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│      recommendations (collaborative filtering)      │
│  anime_id → recommended_anime_id (score, reason)    │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│       seasonal_trends (time-series data)            │
│  anime_id, season, rank_position, views            │
└──────────────────────────────────────────────────────┘
```

---

## Data Ingestion Strategy

### Phase 1 (Now): Minimum Viable
- Anime: title, year, rating, plot, genres, studios
- Embeddings: plot-based semantic search

### Phase 2 (Next): Enhanced
- Characters: Top 5-10 characters per anime
- Related anime: Sequels, prequels, spin-offs
- Themes: Add thematic tags (magic, school, romance)
- MyAnimeList score: Cross-reference for user engagement

### Phase 3 (Polish): Advanced
- Seasonal trends: Rank anime by season
- Recommendations: Compute anime pairs with shared genres/studios
- Voice actors: Link characters to VAs
- Staff: Directors, producers

---

## How to Use in Frontend

### Dashboard Becomes Richer:
```typescript
// Example queries for dashboard

// Trending anime this season
GET /api/stats/trending?season=FALL_2024

// Top characters in anime
GET /api/anime/{id}/characters

// Similar anime
GET /api/anime/{id}/related?type=SEQUEL,SPIN_OFF

// Recommendations based on this anime
GET /api/anime/{id}/recommended

// Seasonal rankings
GET /api/stats/seasonal?season=SPRING_2024&limit=20
```

### Dashboard Visualizations:
- **Trend chart:** Anime popularity over seasons
- **Character grid:** Top characters (images, roles)
- **Related anime:** Graph view of sequels/prequels
- **Seasonal rankings:** Ranked list by season
- **Studio breakdown:** Which studios produce most anime

---

## Implementation Priority

| Phase | Table | Complexity | Value |
|-------|-------|------------|-------|
| **1 (Now)** | `anime`, `studios`, `embeddings` | Low | Core MVP ✅ |
| **2 (Next)** | `characters`, `related_anime` | Medium | Richer data 📊 |
| **2 (Next)** | `recommendations` | Medium | Smart features 🧠 |
| **3 (Polish)** | `seasonal_trends` | Medium | Time-series data 📈 |

---

## My Recommendation

**Start with Phase 1+2 (Medium scope):**

1. Keep anime, studios, embeddings (already set up)
2. Add characters (adds personality to anime)
3. Add related_anime (sequels/prequels are important context)
4. Add recommendations (shows AI integration for dashboard)

**Skip for now:**
- seasonal_trends (nice-to-have, requires external data)
- Staff/VA details (adds complexity, not critical)

**Why this is good for portfolio:**
- Shows data modeling thinking (not just flat tables)
- Demonstrates relationships (many-to-many, graphs)
- Rich enough for interesting dashboard
- Achievable in 2-3 weeks

---

## Revised Timeline

- **Phase 1 (2 days):** Core anime + characters + related_anime tables
- **Phase 2 (3 days):** Enhanced backend (search, stats, recommendations)
- **Phase 3 (3 days):** Frontend with richer visualizations
- **Phase 4 (2 days):** Polish + mobile
- **Phase 5 (1 day):** Deploy

Total: Still 10-12 days, but much more data-rich result.

---

## What Do You Think?

Should I:
- **Option A:** Go with Phase 1+2 (recommended) - richer data, still achievable
- **Option B:** Keep it minimal (Phase 1 only) - faster, simpler
- **Option C:** Add seasonal_trends too - more ambitious, shows trends

Let me know, and I'll update the database schema and ingestion scripts accordingly!
