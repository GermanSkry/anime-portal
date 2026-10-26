# Anime Search Service (Go Microservice)

Production-ready Go microservice for anime search with caching and monitoring.

## Features

- 🚀 **Concurrent Search** — Search anime DB + web simultaneously
- 💾 **Redis Caching** — Save 60-70% SerpAPI quota with 1-hour TTL
- 📊 **Search History** — Track queries and analytics
- 🔍 **Error Tracking** — Sentry integration for production monitoring
- 📈 **Analytics** — PostHog event tracking
- 🐳 **Docker** — Production-ready containerization

## Setup

### Local Development

```bash
# Copy environment variables
cp .env.example .env

# Download dependencies
go mod download

# Run with docker-compose (from root directory)
docker-compose up go-search
```

### Service URLs

- **Service:** `http://localhost:8001`
- **Health:** `GET /health`

## API Endpoints

### Search Web
```bash
POST /api/search/web
{
  "query": "trending anime 2026"
}
```

### Search Anime
```bash
POST /api/search/anime
{
  "query": "action anime"
}
```

### Concurrent Search (Both)
```bash
POST /api/search/concurrent
{
  "query": "naruto anime"
}
```

### Get Search History
```bash
GET /api/search/history
```

### Get Search Stats
```bash
GET /api/search/stats
```

## Architecture

```
Request
  ↓
Cache Check (Redis)
  ├─ Hit? → Return cached
  └─ Miss? → Query source → Cache → Return
  ↓
Log to Database
  ↓
Response
```

## Monitoring

### Sentry (Error Tracking)
- Automatic exception capture
- Performance monitoring
- Deployment tracking

### PostHog (Analytics)
- User search behavior
- API performance
- Cache hit rates

## Performance

- **Cache Hit:** <10ms
- **Cache Miss:** ~1-5s (depends on SerpAPI)
- **Concurrent Search:** ~5-8s (parallel execution)

## Dependencies

- Gin (HTTP framework)
- Redis (caching)
- PostgreSQL (history storage)
- Sentry (error tracking)
- PostHog (analytics)

## Quota Savings

With caching:
- **Before:** 250 searches/month (free tier)
- **After:** 250 searches → ~75-100 actual API calls
- **Savings:** 60-70% reduction

## Future Enhancements

- [ ] SerpAPI batch requests
- [ ] Automatic cache expiration policies
- [ ] GraphQL API layer
- [ ] Rate limiting per IP
- [ ] Search result ranking optimization
