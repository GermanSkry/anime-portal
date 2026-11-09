# Anime Portal: Enhancement Plan (Portfolio Skills)

**Goal:** Add LangGraph agent, Langfuse observability, and Kafka event streaming  
**Timeline:** 10-12 hours total  
**Portfolio Impact:** ⭐⭐⭐ (Demonstrates AI agents, observability, distributed systems)

---

## Phase 1: LangGraph Agent (3-4 hours)

### Goal
Replace current direct Claude calls with a LangGraph agent that:
- Decides which tool to use (anime search, web search, or direct chat)
- Executes tools with proper error handling
- Includes human approval workflow for risky recommendations
- Maintains conversation state

### Architecture

```
User Message
    ↓
LangGraph Agent (State Machine)
    ├─ State: {messages, tool_results, approval_needed}
    ├─ Router Node: Decide next action
    │   ├─ search_anime_db
    │   ├─ search_web
    │   ├─ human_approval (if recommendation score < 0.5)
    │   └─ direct_response
    └─ Response Node: Format and return
    ↓
Frontend handles:
    - Tool calls with pending state
    - Human approval buttons
    - Tool results display
```

### Implementation Steps

#### 1.1 Install Dependencies
```bash
cd backend
pip install langgraph langchain-anthropic langchain
```

#### 1.2 Create LangGraph Agent (`backend/app/utils/langgraph_agent.py`)
```python
from langgraph.graph import StateGraph
from langchain_anthropic import ChatAnthropic
from typing import TypedDict, List, Annotated

class AgentState(TypedDict):
    messages: List[dict]
    tool_results: List[dict]
    requires_approval: bool
    approval_response: str

# Define tools
tools = [
    {
        "name": "search_anime_db",
        "description": "Search anime database by title, genre, year",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "filters": {"type": "object"}
            }
        }
    },
    {
        "name": "search_web",
        "description": "Search web for anime news, reviews, trending",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            }
        }
    }
]

# Build graph
graph_builder = StateGraph(AgentState)

# Add nodes
graph_builder.add_node("router", route_decision)
graph_builder.add_node("search_anime", search_anime_tool)
graph_builder.add_node("search_web", search_web_tool)
graph_builder.add_node("approval", approval_node)
graph_builder.add_node("response", format_response)

# Add edges with conditions
graph_builder.add_conditional_edges(
    "router",
    lambda state: state.get("next_action"),
    {
        "search_anime": "search_anime",
        "search_web": "search_web",
        "approval": "approval",
        "response": "response"
    }
)

agent = graph_builder.compile()
```

#### 1.3 Replace Chat Endpoint (`backend/app/routes/chat.py`)
```python
from app.utils.langgraph_agent import agent

@router.post("/chat")
async def chat(request: ChatRequest, req: Request):
    """Chat with LangGraph agent"""
    state = {
        "messages": request.history or [],
        "tool_results": [],
        "requires_approval": False,
        "approval_response": ""
    }
    
    # Run agent
    result = await agent.ainvoke(state)
    
    # Return response + tool calls if needed
    return ChatResponse(
        response=result["response"],
        tool_calls=result.get("tool_calls", []),
        requires_approval=result.get("requires_approval", False),
        anime_references=result.get("anime_references", [])
    )

@router.post("/chat/approve")
async def approve_recommendation(approval_id: str, approved: bool):
    """Human approval for risky recommendations"""
    # Store approval in state
    # Resume agent execution
```

#### 1.4 Update Frontend to Handle Tool Calls

**New response format:**
```json
{
  "response": "I found some anime...",
  "tool_calls": [
    {
      "id": "tool_1",
      "tool": "search_anime_db",
      "args": {"query": "action"}
    }
  ],
  "requires_approval": false,
  "anime_references": [...]
}
```

**Frontend changes (`Chat.jsx`):**
```jsx
// Handle tool calls
if (response.tool_calls && response.tool_calls.length > 0) {
  setMessages(prev => [...prev, {
    role: 'assistant',
    type: 'tool_calls',
    tools: response.tool_calls
  }])
}

// Handle approval needed
if (response.requires_approval) {
  showApprovalButtons()
}
```

### Success Criteria
- ✅ Agent decides which tool to use
- ✅ Tools execute and return results
- ✅ Human approval workflow works
- ✅ Frontend shows tool execution status
- ✅ Conversation state persists

### Testing
```bash
# Test agent decision
curl -X POST http://localhost:8000/api/chat \
  -d '{"message": "recommend action anime"}'

# Should see tool_calls in response
# Frontend shows: "Searching anime database..."
```

---

## Phase 2: Langfuse Observability (2-3 hours)

### Goal
Add complete tracing for all LLM calls:
- Track inputs/outputs
- Monitor token usage & cost
- Measure latency
- Capture errors
- Dashboard visualization

### Architecture

```
LLM Call
    ↓
OpenAI/Claude API
    ↓
Langfuse (Automatic trace)
    ├─ Input tokens
    ├─ Output tokens
    ├─ Latency
    ├─ Cost
    ├─ Error (if any)
    └─ User/Session context
    ↓
Langfuse Dashboard
    ├─ Call history
    ├─ Cost tracking
    ├─ Performance metrics
    └─ Error analysis
```

### Implementation Steps

#### 2.1 Install & Configure
```bash
cd backend
pip install langfuse

# Add to .env
LANGFUSE_PUBLIC_KEY=pk_***
LANGFUSE_SECRET_KEY=sk_***
LANGFUSE_HOST=https://cloud.langfuse.com  # or local
```

#### 2.2 Create Langfuse Integration (`backend/app/utils/langfuse_tracer.py`)
```python
from langfuse.decorators import observe
from langfuse import Langfuse

langfuse = Langfuse()

@observe()
async def trace_llm_call(messages: list, model: str = "claude-opus"):
    """Automatically traced LLM call"""
    response = await chat_with_claude(messages)
    return response

# Add to Claude agent calls
@observe(name="agent_decision")
async def route_decision(state: AgentState):
    """Traced router decision"""
    decision = ...
    return decision
```

#### 2.3 Wrap LangGraph Agent
```python
from app.utils.langfuse_tracer import trace_llm_call

# In langgraph_agent.py
@observe(name="langgraph_agent")
async def run_agent(state: AgentState):
    result = await agent.ainvoke(state)
    return result

# Each node is automatically traced
# Input/output logged to Langfuse
```

#### 2.4 Add Session/User Context
```python
langfuse.set_current_trace_config({
    "user_id": user_ip,
    "session_id": session_id,
    "tags": ["anime-portal", "chat"]
})
```

#### 2.5 Create Dashboard Endpoint (Optional)
```python
@router.get("/analytics/langfuse")
async def get_langfuse_stats():
    """Return LLM call statistics"""
    return {
        "total_calls": ...,
        "avg_latency": ...,
        "total_cost": ...,
        "error_rate": ...
    }
```

### Langfuse Dashboard Features
- Call history with inputs/outputs
- Token usage breakdown
- Cost per model
- Latency distribution
- Error tracking
- User behavior analysis

### Success Criteria
- ✅ All LLM calls automatically traced
- ✅ Dashboard shows call history
- ✅ Token usage tracked
- ✅ Cost calculation working
- ✅ Error logging functional

### Testing
```bash
# Make a chat request
curl -X POST http://localhost:8000/api/chat \
  -d '{"message": "hello"}'

# View in Langfuse dashboard
# Should see the call logged with:
# - Input: {"message": "hello"}
# - Output: "..."
# - Tokens: input=X, output=Y
# - Latency: Xms
# - Cost: $X.XX
```

---

## Phase 3: Kafka Event Streaming (4-5 hours, Optional)

### Goal
Add event-driven architecture for:
- Notification pipeline
- Search index updates
- User behavior tracking
- Failed message retries
- Idempotent processing

### Architecture

```
Chat Message
    ↓
Kafka Producer
    ↓
Kafka Topics:
├─ chat.messages (new message event)
├─ chat.notifications (send notifications)
├─ search.updates (update search index)
└─ analytics.events (user behavior)
    ↓
Kafka Consumers (Go microservice)
    ├─ Consumer 1: Notification sender
    │   ├─ Retry on failure
    │   ├─ Dead letter queue
    │   └─ Idempotent processing
    ├─ Consumer 2: Search indexer
    └─ Consumer 3: Analytics logger
    ↓
Output:
├─ Email/Push notifications
├─ Updated search index
└─ Analytics database
```

### Implementation Steps

#### 3.1 Setup Docker Compose (Redpanda)
```yaml
# docker-compose.yml (add to existing)
services:
  redpanda:
    image: redpandadata/redpanda:latest
    ports:
      - "9092:9092"      # Kafka API
      - "8081:8081"      # Admin API
    environment:
      REDPANDA_ADVERTISED_KAFKA_API_ADDRESSES: "redpanda:29092"
    command:
      - redpanda
      - start
      - --kafka-addr=PLAINTEXT://0.0.0.0:29092,OUTSIDE://0.0.0.0:9092
```

#### 3.2 Create Kafka Producer (`backend/app/utils/kafka_producer.py`)
```python
from aiokafka import AIOKafkaProducer
import json

producer = None

async def get_producer():
    global producer
    if not producer:
        producer = AIOKafkaProducer(
            bootstrap_servers='localhost:9092',
            value_serializer=lambda v: json.dumps(v).encode()
        )
        await producer.start()
    return producer

async def publish_chat_event(event: dict):
    """Publish chat message event"""
    producer = await get_producer()
    await producer.send_and_wait("chat.messages", event)

# Usage in chat endpoint
await publish_chat_event({
    "user_id": user_ip,
    "message": request.message,
    "timestamp": datetime.now().isoformat()
})
```

#### 3.3 Create Go Consumers (`go-search/consumers/`)
```go
// consumers/notification_consumer.go
package main

import (
    "context"
    "github.com/segmentio/kafka-go"
    "time"
)

type NotificationConsumer struct {
    reader *kafka.Reader
    retryQueue chan kafka.Message
}

func (nc *NotificationConsumer) Start(ctx context.Context) {
    for {
        msg, err := nc.reader.ReadMessage(ctx)
        if err != nil {
            nc.addToRetryQueue(msg)
            continue
        }
        
        // Process message (idempotent)
        if err := nc.processMessage(msg); err != nil {
            nc.addToRetryQueue(msg)
        }
    }
}

func (nc *NotificationConsumer) processMessage(msg kafka.Message) error {
    // Idempotent key: user_id + message_id
    // Check if already processed
    if nc.isProcessed(msg) {
        return nil  // Already processed, skip
    }
    
    // Send notification
    err := sendNotification(msg)
    
    if err != nil {
        return err
    }
    
    // Mark as processed
    nc.markProcessed(msg)
    return nil
}

func (nc *NotificationConsumer) addToRetryQueue(msg kafka.Message) {
    nc.retryQueue <- msg
}
```

#### 3.4 Add Retry & Dead Letter Queue
```python
# backend/app/utils/kafka_retry.py
class RetryManager:
    def __init__(self, max_retries=3, backoff_ms=1000):
        self.max_retries = max_retries
        self.backoff_ms = backoff_ms
    
    async def process_with_retry(self, message):
        for attempt in range(self.max_retries):
            try:
                return await self.process(message)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    # Send to dead letter queue
                    await self.publish_to_dlq(message, e)
                    return
                
                # Exponential backoff
                wait_time = self.backoff_ms * (2 ** attempt)
                await asyncio.sleep(wait_time / 1000)
```

#### 3.5 Create Topics
```bash
# In docker-compose setup
kafka_setup:
  image: redpandadata/redpanda:latest
  command:
    - rpk
    - topic
    - create
    - chat.messages
    - chat.notifications
    - search.updates
    - analytics.events
    - dlq.failed_messages
```

#### 3.6 Wire Up in Chat Endpoint
```python
@router.post("/chat")
async def chat(request: ChatRequest, req: Request):
    # Process chat
    response = await chat_with_claude(...)
    
    # Publish event to Kafka
    await publish_chat_event({
        "type": "chat_message",
        "user_id": get_client_ip(req),
        "message": request.message,
        "response": response,
        "anime_references": response.anime_references,
        "timestamp": datetime.now().isoformat()
    })
    
    return ChatResponse(...)
```

### Event Flow Examples

**Example 1: Notification Pipeline**
```
Chat Message → chat.messages topic
             ↓
Notification Consumer (Go)
             ├─ Extract user_id
             ├─ Check if new anime mentioned
             ├─ Mark as processed (idempotent)
             └─ Send notification → chat.notifications
                       ↓
                    Email/Push service
```

**Example 2: Search Index Update**
```
Chat Message → chat.messages topic
             ↓
Search Indexer Consumer (Go)
             ├─ Extract anime titles
             ├─ Update search index
             └─ Publish to search.updates
```

**Example 3: Retry Logic**
```
Message processing fails
    ↓
Add to retry queue
    ↓
Wait: backoff (1s, 2s, 4s...)
    ↓
Retry (max 3 times)
    ↓
All retries failed?
    ↓
Send to DLQ (dlq.failed_messages)
    ↓
Alert operator
```

### Success Criteria
- ✅ Kafka topics created
- ✅ Chat events published
- ✅ Go consumers reading messages
- ✅ Retry queue working
- ✅ Dead letter queue capturing failures
- ✅ Idempotent processing verified
- ✅ No duplicate notifications

### Testing
```bash
# Produce test message
kafka-console-producer --broker-list localhost:9092 \
  --topic chat.messages \
  --property parse.key=true \
  --property key.separator=: \
  <<< "1:{'user_id':'test','message':'hello'}"

# Consume messages
kafka-console-consumer --bootstrap-server localhost:9092 \
  --topic chat.messages \
  --from-beginning
```

---

## Implementation Checklist

### Phase 1: LangGraph
- [ ] Install langgraph, langchain-anthropic
- [ ] Create AgentState TypedDict
- [ ] Define tools (search_anime, search_web)
- [ ] Build StateGraph with nodes
- [ ] Add conditional routing
- [ ] Replace chat endpoint with agent
- [ ] Update frontend for tool_calls
- [ ] Test agent decisions
- [ ] Deploy & verify

### Phase 2: Langfuse
- [ ] Sign up for Langfuse (free tier)
- [ ] Get API keys
- [ ] Install langfuse SDK
- [ ] Add decorators to LLM calls
- [ ] Set session/user context
- [ ] View dashboard
- [ ] Verify token tracking
- [ ] Check cost calculations
- [ ] Deploy & monitor

### Phase 3: Kafka (Optional)
- [ ] Add Redpanda to docker-compose
- [ ] Create topics
- [ ] Implement Kafka producer
- [ ] Build Go consumers
- [ ] Add retry logic
- [ ] Create dead letter queue
- [ ] Test end-to-end
- [ ] Verify idempotency
- [ ] Deploy & monitor

---

## Portfolio Impact

### What You'll Demonstrate

**LangGraph:**
- Modern agentic AI patterns
- Tool calling & routing
- State machine design
- Human-in-the-loop workflows

**Langfuse:**
- LLM observability & monitoring
- Cost tracking for AI apps
- Production debugging skills
- Analytics integration

**Kafka:**
- Event-driven architecture
- Distributed systems design
- Failure handling & retries
- Idempotent processing patterns

### Talking Points for Interviews

- "I built an agentic chat system using LangGraph that decides which tools to use based on user intent"
- "Implemented Langfuse tracing to track LLM costs, latency, and quality metrics"
- "Designed a Kafka-based event pipeline with retry logic and dead-letter queues for failed messages"
- "Demonstrated idempotent processing patterns to ensure exactly-once semantics in distributed consumers"

---

## Timeline & Dependencies

```
Week 1:
  Mon-Tue: Phase 1 (LangGraph) - 3-4 hours
  Wed:     Phase 2 (Langfuse) - 2-3 hours
  Thu-Fri: Phase 3 (Kafka) - 4-5 hours (optional)

Dependencies:
  Phase 2 requires Phase 1 ✓
  Phase 3 independent (can run anytime)
```

---

## Rollback Plan

Each phase is independently deployable:
- **Phase 1 only:** Agent without tracing (works fine)
- **Phase 1 + 2:** Agent + monitoring (recommended)
- **All phases:** Full event-driven observable system (best)

To disable a phase:
- LangGraph: Revert to direct Claude calls
- Langfuse: Remove decorators, keep agent
- Kafka: Remove event publishing, keep agent

---

## Next Steps

1. Review this plan
2. Start Phase 1 (LangGraph) when ready
3. Add to git as `ENHANCEMENT_PLAN.md`
4. Commit with notes

Ready to begin? 🚀
