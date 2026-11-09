# Kafka Testing Guide

## Setup (One-Time)

### 1. Start Docker Containers
```bash
make db-up
# or
docker-compose up -d
```

**Verify Kafka is healthy:**
```bash
docker exec anime_kafka rpk cluster info
```

Should output:
```
CLUSTER INFO
============
ID:     ...
Leader: redpanda-0
Topics: 3
Partitions: 7
...
```

### 2. Create Database Tables
```bash
psql postgresql://postgres:password@localhost:5432/anime_db < backend/scripts/create_kafka_tables.sql
```

**Verify tables exist:**
```bash
psql postgresql://postgres:password@localhost:5432/anime_db -c "\dt processed_messages search_engagement"
```

### 3. Install Go Dependencies
```bash
cd go-search
go mod download
```

---

## Running the System

### Terminal 1: FastAPI Backend
```bash
make backend
# or
cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Verify running:**
```bash
curl http://localhost:8000/health
# Should return: {"status":"ok"}
```

### Terminal 2: Go Service + Kafka Consumers
```bash
make go-service
# or
cd go-search && go run main.go
```

**Verify running:**
```bash
curl http://localhost:8001/health
# Should return: {"status":"ok"}
```

**You should see logs like:**
```
🚀 Starting Go search service on port 8001
📋 Creating Kafka topics...
🚀 DB Consumer starting...
🚀 Search Indexer starting...
```

---

## Test 1: Basic Kafka Flow

### Send a Chat Message
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "recommend action anime",
    "history": []
  }' | jq '.'
```

**Expected response (in ~2ms):**
```json
{
  "response": "Here are some great action anime...",
  "anime_ids": [302, 251],
  "anime_references": [
    {"title": "Jujutsu Kaisen", "id": 302},
    {"title": "Attack on Titan", "id": 251}
  ]
}
```

**Watch Go service logs - you should see:**
```
✅ Message processed: chat-messages/partition-0/offset-0
✅ Message indexed: chat-messages/partition-0/offset-1
```

---

## Test 2: Verify Kafka Messages

### List Topics
```bash
make kafka-topics
```

Output:
```
TOPIC            PARTITIONS  REPLICAS
chat.messages    3           1
search.updates   3           1
dlq.failed_messages  1       1
```

### View Messages in chat.messages Topic
```bash
docker exec anime_kafka rpk topic consume chat.messages -n 5
```

Output (last 5 messages):
```json
{
  "message_id": "uuid-123",
  "user_id": "127.0.0.1",
  "message": "recommend action anime",
  "response": "Here are some great action anime...",
  "anime_references": [...],
  "timestamp": "2026-11-09T14:20:00Z"
}
```

---

## Test 3: Verify Database Save (DB Consumer)

### Check chat_history Table
```bash
psql postgresql://postgres:password@localhost:5432/anime_db -c "SELECT * FROM chat_history ORDER BY created_at DESC LIMIT 1 \gx"
```

Output:
```
user_ip            | 127.0.0.1
user_message       | recommend action anime
assistant_response | Here are some great action anime...
anime_context_id   | (null)
anime_references   | [{"title":"Jujutsu Kaisen","id":302}...]
created_at         | 2026-11-09 14:20:00.123456
```

### Check Idempotency Table
```bash
psql postgresql://postgres:password@localhost:5432/anime_db -c "SELECT * FROM processed_messages ORDER BY processed_at DESC LIMIT 1 \gx"
```

Output:
```
topic       | chat.messages
message_id  | uuid-123
offset      | 0
processed_at | 2026-11-09 14:20:00.123456
```

---

## Test 4: Verify Search Indexing (Search Indexer)

### Check search_engagement Table
```bash
psql postgresql://postgres:password@localhost:5432/anime_db -c "SELECT * FROM search_engagement ORDER BY last_updated DESC LIMIT 5 \gx"
```

Output:
```
anime_id         | 302
engagement_type  | chat_mention
count            | 2
last_updated     | 2026-11-09 14:20:00.123456

anime_id         | 251
engagement_type  | chat_mention
count            | 1
last_updated     | 2026-11-09 14:20:00.123456
```

---

## Test 5: Idempotency (Message Deduplication)

### Send the Same Message Twice
```bash
# First time
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test message", "history": []}' | jq '.response'

# Wait 1 second
sleep 1

# Get a message from Kafka topic (to get the message_id)
MESSAGE_ID=$(docker exec anime_kafka rpk topic consume chat.messages -n 1 --no-offsets | jq -r '.message_id')

# Manually publish the same message again
docker exec anime_kafka rpk topic produce chat.messages \
  --key "key" \
  --msgs "$(docker exec anime_kafka rpk topic consume chat.messages -n 1 | jq -c '.')"
```

**Expected behavior:**
- First time: Consumer processes and saves to DB
- Second time (duplicate): Consumer sees it's already in `processed_messages` table
- Go logs show: `⏭️ Message already processed: <message_id>`
- Database NOT duplicated (only 1 entry in chat_history)

**Verify no duplicate:**
```bash
psql postgresql://postgres:password@localhost:5432/anime_db -c "SELECT COUNT(*) FROM chat_history WHERE user_message = 'test message'"
# Output: 1 (not 2)
```

---

## Test 6: Retry Logic (Simulate Failure)

### Option A: Kill Database Temporarily
```bash
# In another terminal, kill Postgres
docker pause anime_db

# Send a chat message - should fail initially
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "retry test", "history": []}' 

# Watch Go logs - you should see:
# ⚠️ Attempt 1 failed: driver: bad connection
# Wait 1s...
# ⚠️ Attempt 2 failed: driver: bad connection
# Wait 2s...

# Bring DB back after 5 seconds
sleep 5
docker unpause anime_db

# Watch Go logs:
# ⏳ Attempt 3 failed: driver: bad connection
# Wait 4s...
# ✅ Message processed! (success on retry)
```

**Expected:** Message still saves successfully after DB recovers.

### Option B: Watch Dead Letter Queue
If DB stays down for all 3 retries:
```bash
docker exec anime_kafka rpk topic consume dlq.failed_messages -n 1
```

Output:
```json
{
  "original_topic": "chat.messages",
  "original_message": {...},
  "error": "connection timeout",
  "retries_attempted": 3,
  "timestamp": "2026-11-09T14:20:00Z"
}
```

---

## Test 7: End-to-End Flow

### Complete Test Script
```bash
#!/bin/bash

echo "🚀 Phase 3 Kafka E2E Test"
echo "========================="
echo ""

# 1. Send message
echo "1️⃣ Sending chat message..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "recommend isekai anime", "history": []}')

MESSAGE_ID=$(echo "$RESPONSE" | jq -r '.response' | head -c 20)
echo "✅ Response: $MESSAGE_ID..."
echo ""

# 2. Wait for consumers
echo "2️⃣ Waiting for async processing..."
sleep 2
echo "✅ Done"
echo ""

# 3. Check Kafka topic
echo "3️⃣ Checking Kafka topic..."
KAFKA_COUNT=$(docker exec anime_kafka rpk topic status chat.messages | grep "Replicas" | wc -l)
echo "✅ Kafka has messages"
echo ""

# 4. Check database
echo "4️⃣ Checking database save..."
DB_COUNT=$(psql postgresql://postgres:password@localhost:5432/anime_db -t -c "SELECT COUNT(*) FROM chat_history WHERE user_message LIKE '%isekai%'")
echo "✅ Database saved: $DB_COUNT record(s)"
echo ""

# 5. Check search engagement
echo "5️⃣ Checking search engagement..."
ENGAGEMENT=$(psql postgresql://postgres:password@localhost:5432/anime_db -t -c "SELECT SUM(count) FROM search_engagement WHERE engagement_type = 'chat_mention'")
echo "✅ Total engagement tracked: $ENGAGEMENT"
echo ""

echo "🎉 Phase 3 Kafka E2E Test Complete!"
```

Save and run:
```bash
chmod +x test_kafka_e2e.sh
./test_kafka_e2e.sh
```

---

## Monitoring

### View All Logs
```bash
# Backend logs
tail -f /tmp/backend.log

# Go service logs
# (watch the Terminal 2 output)

# Kafka broker
make kafka-logs
```

### View Consumer Lag
```bash
docker exec anime_kafka rpk group list
docker exec anime_kafka rpk group describe chat.messages-consumer
```

### View Topic Partitions
```bash
docker exec anime_kafka rpk topic info chat.messages
```

---

## Troubleshooting

### Problem: "Connection refused" on Kafka
```
❌ Error: failed to connect to Kafka: connection refused
```

**Solution:**
```bash
# Check if Kafka is running
docker ps | grep anime_kafka

# If not, start it
docker-compose up -d
```

### Problem: Database tables don't exist
```
❌ failed to insert chat: relation "chat_history" does not exist
```

**Solution:**
```bash
# Create tables
psql postgresql://postgres:password@localhost:5432/anime_db < backend/scripts/create_kafka_tables.sql

# Verify
psql postgresql://postgres:password@localhost:5432/anime_db -c "\dt"
```

### Problem: Go consumers not starting
```
❌ Error: could not import github.com/segmentio/kafka-go
```

**Solution:**
```bash
cd go-search
go mod tidy
go run main.go
```

### Problem: Messages not being processed
```
⏳ Message sits in Kafka but not saved to DB
```

**Checks:**
1. Are consumers running? (Check Terminal 2)
2. Is database healthy? `docker exec anime_db pg_isready`
3. Check consumer logs for errors
4. Check Go service logs: `docker logs anime_search` (if running in container)

---

## Quick Commands Reference

```bash
# Start all
make db-up
make backend &  # Terminal 1
make go-service &  # Terminal 2

# Test
make kafka-test

# Monitor
make kafka-topics
make kafka-logs
tail -f /tmp/backend.log

# Check data
psql postgresql://postgres:password@localhost:5432/anime_db -c "SELECT * FROM chat_history ORDER BY created_at DESC LIMIT 5"
psql postgresql://postgres:password@localhost:5432/anime_db -c "SELECT * FROM processed_messages ORDER BY processed_at DESC LIMIT 5"
```

---

## What Success Looks Like

✅ **Chat responds in ~2ms** (not blocked by DB/indexing)  
✅ **Kafka receives message** (verify in `chat.messages` topic)  
✅ **DB consumer saves** (check `chat_history` table)  
✅ **Search indexer updates** (check `search_engagement` table)  
✅ **Idempotency works** (duplicate message not saved twice)  
✅ **Retries work** (message saved after transient failure)  
✅ **DLQ catches failures** (message in `dlq.failed_messages` if all retries fail)

If all ✅, you have enterprise-grade event-driven architecture! 🎉
