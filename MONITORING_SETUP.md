# Monitoring Setup Guide

## Overview

The anime portal has integrated professional monitoring with:
- **PostHog**: Analytics & event tracking (EU instance)
- **Sentry**: Error tracking & performance monitoring

Both are configured but require final setup steps.

---

## PostHog Setup ✅ COMPLETE

### Configuration
- **API Key**: `phc_BAGL9csE454SiWZincoFkR6bMB45deop7g7S6C2vJm3g`
- **Project ID**: 321264
- **Region**: EU Cloud (`eu.i.posthog.com`)
- **Status**: ✅ Active and tracking events

### Events Being Tracked
```
Search Events:
- search_performed (query, result_count, query_type, duration)
- cache_hit (query, timestamp)
- cache_miss (query, timestamp)
- api_call (api: "serpapi", success, duration_ms)
```

### Where to View
1. Go to https://eu.posthog.com
2. Login with your account
3. Select project "321264" (Anime Vibe)
4. View events in real-time under "Events" tab

### Dashboard Metrics
- **Search Funnel**: query → results → click
- **Cache Performance**: Hit rate & performance improvement
- **API Performance**: SerpAPI response times
- **Query Trends**: Popular searches, trending anime

---

## Sentry Setup ⏳ REQUIRES DSN

### Current Status
- Framework installed in both services
- Awaiting Sentry DSN configuration

### To Get Your Sentry DSN

**Option A: Using CLI (Recommended)**
```bash
npx @sentry/agent-plugin install animevibe#d06cb636fb
```
The tool will:
- Detect your Sentry org (animevibe)
- Create projects for Python & Go
- Generate DSN automatically
- Update your .env files

**Option B: Manual Setup**
1. Go to https://sentry.io/organizations/animevibe/projects/
2. Create a new project:
   - Name: "anime-portal-backend" (Python FastAPI)
   - Platform: Python
   - Alert me on every new issue: ✓
3. Create another:
   - Name: "anime-portal-go" (Go microservice)
   - Platform: Go
4. Copy the DSN for each project

### Add DSN to Environment

**Go Service** (`go-search/.env`):
```env
SENTRY_DSN=https://<key>@sentry.io/<project-id>
```

**Python Backend** (`backend/.env`):
```env
SENTRY_DSN=https://<key>@sentry.io/<project-id>
```

### Restart Services
```bash
# Kill existing services
pkill search-service
pkill uvicorn

# Restart with Sentry enabled
cd go-search && PORT=8001 ./search-service &
cd ../backend && uvicorn main:app --port 8000 &
```

---

## Monitoring Events

### Sentry Tracks
- ✅ Exceptions (automatic)
- ✅ Database errors
- ✅ API failures
- ✅ Performance metrics (response times)
- ✅ Deployment tracking

### PostHog Tracks
- ✅ User search behavior
- ✅ Cache performance
- ✅ API quotas used
- ✅ Popular queries

---

## Dashboards to Create

### PostHog Dashboards
1. **Real-Time Activity**
   - Live search queries
   - Cache hit rate
   - API response times

2. **Performance Metrics**
   - P50, P95, P99 latency
   - Cache efficiency %
   - Quota usage vs limit

3. **Business Metrics**
   - Top 10 searches
   - Unique users/searches
   - Feature adoption (web search, anime search, concurrent)

### Sentry Dashboards
1. **Error Tracking**
   - Error rate by service
   - Most common errors
   - Error trends

2. **Performance**
   - Response time distribution
   - Slowest endpoints
   - Database query performance

3. **Releases**
   - Deployment tracking
   - Error rate per release
   - Performance impact of deploys

---

## Testing the Setup

### Test PostHog Events
```bash
# Make some searches
curl -X POST http://localhost:8001/api/search/web \
  -H "Content-Type: application/json" \
  -d '{"query":"test anime"}'

# Check PostHog Events dashboard
# You should see search_performed events appear in ~5 seconds
```

### Test Sentry Error Tracking
Once DSN is configured:
```bash
# Trigger an error (wrong database connection)
# Or manually test in code:

# Python:
from sentry_sdk import capture_exception
try:
    raise Exception("Test error")
except Exception as e:
    capture_exception(e)

# Go:
sentry.CaptureException(errors.New("Test error"))
```

---

## Production Alerts

### Recommended Sentry Alerts
1. **New Issue**: Alert on any new error
2. **Regression**: Alert if error rate increases
3. **Release Health**: Alert on bad deploys
4. **Quota**: Alert when approaching SerpAPI limit

### Setting Up
1. Go to Sentry dashboard
2. Alerts → Create Alert Rule
3. Set conditions (error rate, issue type, etc.)
4. Notification: Email / Slack / PagerDuty

---

## Monitoring Checklist

- [ ] PostHog events showing in dashboard
- [ ] Sentry DSN obtained from Sentry UI
- [ ] SENTRY_DSN added to `go-search/.env`
- [ ] SENTRY_DSN added to `backend/.env`
- [ ] Services restarted with Sentry enabled
- [ ] Test error manually triggers Sentry alert
- [ ] Error dashboards created in Sentry
- [ ] Performance dashboards created in PostHog
- [ ] Alerts configured (email/Slack notifications)
- [ ] Team members invited to both platforms

---

## Quick Reference

### Environment Variables
```bash
# PostHog (already set)
POSTHOG_API_KEY=phc_BAGL9csE454SiWZincoFkR6bMB45deop7g7S6C2vJm3g
POSTHOG_REGION=eu

# Sentry (to be added)
SENTRY_DSN=https://<key>@sentry.io/<project-id>

# Environment
ENVIRONMENT=production
```

### Service Startup with Monitoring
```bash
# Go service
cd go-search
SENTRY_DSN="<your-dsn>" \
POSTHOG_API_KEY="phc_BAGL9csE454SiWZincoFkR6bMB45deop7g7S6C2vJm3g" \
PORT=8001 \
./search-service

# Python backend
cd backend
SENTRY_DSN="<your-dsn>" \
POSTHOG_API_KEY="phc_BAGL9csE454SiWZincoFkR6bMB45deop7g7S6C2vJm3g" \
python -m uvicorn main:app --port 8000
```

---

## Support

For issues:
- PostHog Docs: https://posthog.com/docs
- Sentry Docs: https://docs.sentry.io
- Discord: Contact your account manager

