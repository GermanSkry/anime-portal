# Phase 3: Kafka Event Streaming Architecture for Anime Portal

## Overview

Kafka transforms your system from **request-response** into **event-driven**. Instead of the chat endpoint doing everything synchronously, it publishes events that independent consumers process asynchronously.

**Without Kafka (Current):**
```
User Message
    ↓
Chat Endpoint (blocking)
├─ Call Claude
├─ Save to DB (wait)
├─ Extract references (wait)
└─ Return response to user
```

**With Kafka (Phase 3):**
```
User Message
    ↓
Chat Endpoint (fast, non-blocking)
├─ Validate input
├─ Publish to Kafka
└─ Return response immediately
    ↓
Kafka Topics (async processing)
├─ Consumer 1: Save to DB
├─ Consumer 2: Send notifications
├─ Consumer 3: Update search index
├─ Consumer 4: Track analytics
└─ Consumer 5: Update recommendation engine
```

---

## Why Kafka for Anime Portal?

### Problem It Solves
1. **Latency**: Chat endpoint shouldn't wait for database saves
2. **Scalability**: Multiple consumers can process events independently
3. **Reliability**: Events aren't lost if a consumer crashes (retry queue)
4. **Decoupling**: Chat service doesn't know about notifications, indexing, analytics
5. **Throughput**: Handle spikes without blocking the main API

### Real Example
```
User sends: "recommend action anime"
Claude responds in 2 seconds

WITHOUT Kafka (blocking):
- Save to DB: +200ms
- Extract references: +100ms
- Index for search: +150ms
- Send notification: +300ms
- Track analytics: +50ms
Total: 2 + 0.8 = 2.8 seconds ❌ User waits

WITH Kafka (async):
- Publish to Kafka: +10ms
Total: 2 + 0.01 = 2.01 seconds ✅ User gets response immediately
[Background: DB, indexing, notifications all happen in parallel]
```

---

## Architecture: Kafka Topics & Consumers

### Topic 1: `chat.messages` (Chat Endpoint publishes)
**Event Structure:**
```json
{
  "message_id": "uuid",
  "user_id": "192.168.1.1",
  "message": "recommend action anime",
  "response": "Here are some...",
  "anime_references": [
    {"title": "Jujutsu Kaisen", "id": 302}
  ],
  "timestamp": "2026-11-09T14:17:13Z"
}
```

**Consumers:**
- `Consumer 1 (DB Saver)` → Save to PostgreSQL `chat_history` table
- `Consumer 2 (Notification)` → Send email/push notification if needed
- `Consumer 3 (Search Indexer)` → Update Elasticsearch/search index
- `Consumer 4 (Analytics)` → Track metrics (messages/hour, avg response time)

### Topic 2: `chat.notifications` (Derived from messages)
**Event Structure:**
```json
{
  "user_id": "192.168.1.1",
  "type": "new_recommendation",
  "title": "Action Anime Recommendations",
  "anime_count": 4,
  "timestamp": "2026-11-09T14:17:13Z"
}
```

**Consumer:**
- `Notification Service (Go)` → Send via email, push, or webhook

### Topic 3: `search.updates` (Derived from messages)
**Event Structure:**
```json
{
  "anime_ids": [302, 251, 304],
  "operation": "add_to_index",
  "message_id": "uuid",
  "timestamp": "2026-11-09T14:17:13Z"
}
```

**Consumer:**
- `Search Indexer (Go)` → Update Elasticsearch/Meilisearch

---

## Failure Handling: Retries & Dead Letter Queue

### Problem: What if a consumer crashes?

```
Kafka Message
    ↓
Consumer tries to save to DB
    ↓
DB connection fails → Exception
    ↓
Option 1: Retry (configurable backoff)
├─ Wait 1 second
├─ Retry 1: Still fails
├─ Wait 2 seconds
├─ Retry 2: Still fails
├─ Wait 4 seconds
├─ Retry 3: Success ✅

Option 2: Max retries exceeded
    ↓
Send to Dead Letter Queue (DLQ)
    ↓
Operator reviews & manually reprocesses
```

### Retry Configuration (Exponential Backoff)
```python
class RetryConfig:
    max_retries = 3
    backoff_ms = [1000, 2000, 4000]  # 1s, 2s, 4s
    # Attempt 1 fails → wait 1s → Retry 1
    # Retry 1 fails → wait 2s → Retry 2
    # Retry 2 fails → wait 4s → Retry 3
    # Retry 3 fails → send to DLQ
```

### Dead Letter Queue Topic: `dlq.failed_messages`
```json
{
  "original_topic": "chat.messages",
  "original_message": {...},
  "error": "Connection timeout",
  "retries_attempted": 3,
  "timestamp": "2026-11-09T14:17:13Z"
}
```

**DLQ Consumer:**
- `Operator Alerts` → Send to Sentry/PagerDuty
- `Manual Replay Tool` → Operator can fix issue & reprocess

---

## Idempotent Processing: No Duplicate Processing

### Problem: What if a message is processed twice?

```
Message published to Kafka
    ↓
Consumer 1 saves to DB
    ↓
Response to consumer: "Saved!"
    ↓
Network glitch → Kafka doesn't receive ACK
    ↓
Kafka thinks: "Message not processed, resend"
    ↓
Consumer 1 receives message AGAIN
    ↓
Saves to DB AGAIN (duplicate!)
```

### Solution: Idempotent Key

```python
class IdempotentProcessor:
    def __init__(self):
        self.processed = set()  # In-memory cache or Redis
    
    def process_message(self, message):
        idempotent_key = f"{message.topic}:{message.message_id}:{message.offset}"
        
        # Check if already processed
        if idempotent_key in self.processed:
            logger.info(f"Already processed: {idempotent_key}")
            return  # Skip duplicate
        
        # Process message
        result = self.do_work(message)
        
        # Mark as processed
        self.processed.add(idempotent_key)
        
        return result

# Example:
# First run:  process_message("chat.messages:uuid-123:offset-456")
# Second run: process_message("chat.messages:uuid-123:offset-456")
# Output: "Already processed, skipping"
```

**Database Implementation (More Reliable):**
```sql
-- Track processed messages in DB
CREATE TABLE processed_messages (
    topic VARCHAR(50),
    message_id UUID,
    offset BIGINT,
    processed_at TIMESTAMP,
    PRIMARY KEY (topic, message_id, offset)
);

-- On consumer startup
SELECT * FROM processed_messages 
WHERE message_id = 'abc-123'
-- If exists: skip
-- If not exists: process & insert row
```

---

## Go Microservice: Kafka Consumers

### Consumer Structure

```go
// go-search/consumers/db_consumer.go
package main

import (
    "github.com/segmentio/kafka-go"
    "database/sql"
    "context"
)

type DBConsumer struct {
    reader *kafka.Reader
    db     *sql.DB
    config RetryConfig
}

func (c *DBConsumer) Start(ctx context.Context) {
    for {
        msg, err := c.reader.FetchMessage(ctx)
        if err != nil {
            log.Fatal(err)
        }
        
        // With retries
        if err := c.processWithRetry(msg); err != nil {
            c.sendToDLQ(msg, err)
            continue
        }
        
        // Mark as processed
        c.reader.CommitMessages(ctx, msg)
    }
}

func (c *DBConsumer) processWithRetry(msg kafka.Message) error {
    var lastErr error
    
    for attempt := 0; attempt < c.config.MaxRetries; attempt++ {
        lastErr = c.saveToDatabase(msg)
        
        if lastErr == nil {
            return nil  // Success
        }
        
        // Exponential backoff
        wait := c.config.BackoffMs[attempt]
        time.Sleep(time.Duration(wait) * time.Millisecond)
    }
    
    return lastErr  // All retries failed
}

func (c *DBConsumer) saveToDatabase(msg kafka.Message) error {
    var event ChatMessageEvent
    json.Unmarshal(msg.Value, &event)
    
    // Check if already processed (idempotent)
    var exists bool
    err := c.db.QueryRow(
        "SELECT EXISTS(SELECT 1 FROM processed_messages WHERE message_id = $1)",
        event.MessageID,
    ).Scan(&exists)
    
    if exists {
        return nil  // Already processed
    }
    
    // Save to chat_history
    _, err = c.db.Exec(
        "INSERT INTO chat_history (user_ip, user_message, assistant_response, anime_references) VALUES ($1, $2, $3, $4)",
        event.UserID, event.Message, event.Response, event.AnimeReferences,
    )
    
    if err != nil {
        return err
    }
    
    // Mark as processed
    c.db.Exec(
        "INSERT INTO processed_messages (topic, message_id, offset) VALUES ($1, $2, $3)",
        "chat.messages", event.MessageID, msg.Offset,
    )
    
    return nil
}
```

---

## Implementation Steps

### Step 1: Setup Redpanda (In Docker Compose)
```yaml
services:
  redpanda:
    image: redpandadata/redpanda:latest
    ports:
      - "9092:9092"      # Kafka API
      - "8081:8081"      # Admin API
    environment:
      REDPANDA_ADVERTISED_KAFKA_API_ADDRESSES: "redpanda:29092"
```

### Step 2: Create Topics
```bash
rpk topic create chat.messages
rpk topic create chat.notifications
rpk topic create search.updates
rpk topic create dlq.failed_messages
```

### Step 3: Update Chat Endpoint (FastAPI)
```python
# backend/app/routes/chat.py

from aiokafka import AIOKafkaProducer
import json

@router.post("/chat")
async def chat(request: ChatRequest, req: Request):
    # ... call agent ...
    
    # Publish to Kafka (non-blocking)
    producer = get_kafka_producer()
    
    event = {
        "message_id": str(uuid.uuid4()),
        "user_id": get_client_ip(req),
        "message": request.message,
        "response": response_text,
        "anime_references": anime_references,
        "timestamp": datetime.now().isoformat()
    }
    
    # Fire and forget - don't wait for consumer
    await producer.send_and_wait("chat.messages", json.dumps(event).encode())
    
    # Return immediately to user (2ms instead of 800ms!)
    return ChatResponse(response=response_text, ...)
```

### Step 4: Build Go Consumers
```
go-search/consumers/
├── db_consumer.go          # Saves to PostgreSQL
├── notification_consumer.go # Sends emails/push
├── search_indexer.go       # Updates search index
└── analytics_consumer.go    # Tracks metrics
```

---

## Real-World Scenarios

### Scenario 1: Database Overload
```
Normal flow: Chat waits for DB save (blocking)
Spike: 100 concurrent users
Result: DB can't handle 100 writes → Chat API times out ❌

With Kafka:
Chat endpoint: Publish to Kafka (instant)
Consumers: Process 100 writes at their own pace with retries
Result: Chat responds in 2ms regardless of DB load ✅
```

### Scenario 2: Notification Service Down
```
Without Kafka:
User sends message
Chat tries to send notification
Notification service is down (500 error)
Chat endpoint crashes ❌
User gets error

With Kafka:
User sends message
Event published to Kafka (no error)
Chat responds successfully to user ✅
Notification consumer crashes
Event stays in Kafka (not lost)
Consumer restarts
Notification is sent (delayed but reliable) ✅
```

### Scenario 3: Adding New Feature (Search Indexing)
```
Without Kafka:
Need to update chat endpoint
Add: "index anime in search"
Risk: If indexing fails, whole chat fails

With Kafka:
Add: New `search.updates` consumer
Existing chat endpoint: No changes needed
Risk: Zero (decoupled) ✅
Just add consumer: Done
```

---

## Portfolio Impact: Phase 3

When implemented, you'll demonstrate:

### Architecture Skills:
- **Event-driven design** (vs request-response)
- **Asynchronous processing** (non-blocking)
- **Reliability patterns** (retries, DLQ, idempotency)
- **Distributed systems** (multiple independent consumers)
- **System decoupling** (services don't know about each other)

### Interview Talking Points:
> "Our anime portal uses Kafka to decouple the chat endpoint from downstream operations. When a user sends a message, the API publishes an event and responds immediately—it doesn't wait for the database, notifications, or search indexing. Consumers process events independently with exponential backoff retries and dead letter queues for fault tolerance. We use idempotent keys to ensure exactly-once semantics even if Kafka redelivers messages."

### Real Companies Using This Pattern:
- **Uber**: Orders → multiple consumers (payments, notifications, analytics)
- **Airbnb**: Bookings → multiple consumers (email, search index, analytics)
- **Netflix**: User events → multiple consumers (recommendations, analytics, logging)

---

## Timeline & Effort

| Phase | Effort | Skills | Status |
|-------|--------|--------|--------|
| Phase 1: LangGraph | 3-4 hrs | AI agents, tool calling | ✅ DONE |
| Phase 2: Langfuse | 2-3 hrs | Observability, tracing | ✅ DONE |
| **Phase 3: Kafka** | **4-5 hrs** | **Event-driven arch, reliability** | ⏳ Optional |

---

## Decision: Should We Do Phase 3?

### Go for it if:
- ✅ You want to show distributed systems skills
- ✅ You're applying to backend/infrastructure roles
- ✅ You want to demonstrate reliability patterns
- ✅ You have 4-5 hours

### Skip if:
- ❌ You want to ship quickly (Phase 1+2 already strong)
- ❌ You prefer simpler architecture
- ❌ Running low on time

### My Take:
**Phase 1 + 2 is already strong portfolio material.** Phase 3 is the "cherry on top" that separates strong backend engineers from great ones. If you have the time, it's worth it—Kafka experience is valuable.

---

## Next: Let's Build Phase 3?

Ready to implement Kafka consumers? I can:
1. Setup Redpanda in docker-compose
2. Create Kafka producer in chat endpoint
3. Build 2-3 Go consumers (DB, notifications, search)
4. Add retry logic + dead letter queue
5. Implement idempotent processing

**What do you want to do?**
- 🚀 Go all-in on Phase 3 (4-5 hours)
- 📊 Just understand it for now
- ✅ Consider it done (Phase 1+2 is enough)
