"""Chat endpoint with LangGraph agent + Langfuse tracing + Kafka publishing"""
import json
import logging
import os
import re
import uuid
from datetime import datetime

import psycopg
from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.config import settings
from app.utils.langfuse_tracer import log_trace_event, set_user_context, trace_llm_call
from app.utils.langgraph_agent import run_agent

kafka_producer = None

async def get_kafka_producer():
    """Get or create Kafka producer"""
    global kafka_producer
    if kafka_producer is None:
        kafka_brokers = os.getenv("KAFKA_BROKERS", "localhost:9092")
        producer = AIOKafkaProducer(
            bootstrap_servers=kafka_brokers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        # only cache after a successful start, otherwise every later call reuses a dead producer
        try:
            await producer.start()
        except Exception:
            await producer.stop()
            raise
        kafka_producer = producer
    return kafka_producer

async def close_kafka_producer():
    """Close Kafka producer on shutdown"""
    global kafka_producer
    if kafka_producer:
        await kafka_producer.stop()
        kafka_producer = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] | None = None
    anime_id: int | None = None

class AnimeReference(BaseModel):
    title: str
    id: int

class ChatResponse(BaseModel):
    response: str
    anime_ids: list[int] = []
    anime_references: list[AnimeReference] = []

class ChatHistoryItem(BaseModel):
    id: int
    user_message: str
    assistant_response: str
    anime_context_id: int | None
    anime_references: list[AnimeReference] = []
    created_at: str

def get_client_ip(request: Request) -> str:
    """Extract client IP from request headers"""
    if request.client:
        return request.client.host
    return request.headers.get("x-forwarded-for", "unknown").split(",")[0].strip()

async def extract_anime_references(response_text: str) -> list[AnimeReference]:
    """Extract anime titles from response and find their IDs in database"""
    import re

    # Find all **Title** patterns in the response
    pattern = r'\*\*([^*]+)\*\*'
    titles = re.findall(pattern, response_text)

    if not titles:
        return []

    references = []
    conn = await psycopg.AsyncConnection.connect(settings.database_url)

    try:
        for title in titles:
            # Skip if already added
            if any(ref.title == title for ref in references):
                continue

            async with conn.cursor() as cur:
                # Search for anime by title (case-insensitive)
                await cur.execute("""
                    SELECT id, title_english, title
                    FROM anime
                    WHERE LOWER(title_english) ILIKE LOWER(%s)
                       OR LOWER(title) ILIKE LOWER(%s)
                    LIMIT 1
                """, (f"%{title}%", f"%{title}%"))

                result = await cur.fetchone()
                if result:
                    anime_id = result[0]
                    # Use the title as it appears in the response (not DB title)
                    references.append(AnimeReference(title=title, id=anime_id))
    finally:
        await conn.close()

    return references

async def save_chat_message(user_ip: str, user_msg: str, assistant_msg: str, anime_id: int | None = None, anime_references: list[AnimeReference] | None = None):
    """Save chat message to database"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)
    try:
        async with conn.cursor() as cur:
            refs_json = json.dumps([{"title": ref.title, "id": ref.id} for ref in (anime_references or [])])

            await cur.execute("""
                INSERT INTO chat_history (user_ip, user_message, assistant_response, anime_context_id, anime_references)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_ip, user_msg, assistant_msg, anime_id, refs_json))
        await conn.commit()
    except Exception as e:
        logger.error(f"Error saving chat: {e}", exc_info=True)
    finally:
        await conn.close()

@router.post("/chat")
@trace_llm_call(name="anime_chat", tags=["chat", "anime"])
async def chat(request: ChatRequest, req: Request) -> ChatResponse:
    """Chat with LangGraph agent. Publishes to Kafka for async processing."""

    user_ip = get_client_ip(req)
    set_user_context(user_ip, tags=["anime-portal"])

    log_trace_event("chat_start", {"user": user_ip, "message": request.message[:50]})

    # Build message history
    messages = []

    if request.history:
        for m in request.history:
            messages.append({
                "role": m.role,
                "content": m.content
            })

    # Add current message
    messages.append({
        "role": "user",
        "content": request.message
    })

    log_trace_event("history_built", {"message_count": len(messages)})

    # Run LangGraph agent
    result = await run_agent(messages)
    response_text = result["response"]
    tool_calls = result["tool_calls"]
    anime_references_list = result["anime_references"]

    log_trace_event("agent_response", {"response_length": len(response_text), "tool_calls": len(tool_calls)})

    # Convert to AnimeReference objects
    anime_references = []
    for ref in anime_references_list:
        title = ref.get("title", "")
        anime_id = await lookup_anime_by_title(title)
        if anime_id:
            anime_references.append(AnimeReference(title=title, id=anime_id))

    log_trace_event("references_found", {"count": len(anime_references)})

    # Publish to Kafka for async processing (DB save, search indexing)
    try:
        producer = await get_kafka_producer()
        message_id = str(uuid.uuid4())

        event = {
            "message_id": message_id,
            "user_id": user_ip,
            "message": request.message,
            "response": response_text,
            "anime_references": [{"title": ref.title, "id": ref.id} for ref in anime_references],
            "anime_context_id": request.anime_id,
            "timestamp": datetime.now().isoformat()
        }

        await producer.send_and_wait("chat.messages", event)
        log_trace_event("kafka_published", {"message_id": message_id})
    except Exception as e:
        # Kafka is the only route to chat_history, so write it here instead of losing it
        logger.warning(f"Kafka publish failed, saving chat directly: {e}")
        log_trace_event("kafka_error", {"error": str(e)})
        await save_chat_message(user_ip, request.message, response_text, request.anime_id, anime_references)

    return ChatResponse(
        response=response_text,
        anime_ids=[ref.id for ref in anime_references],
        anime_references=anime_references
    )

async def lookup_anime_by_title(title: str) -> int | None:
    """Look up anime ID by title"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id FROM anime WHERE LOWER(title_english) ILIKE LOWER(%s) OR LOWER(title) ILIKE LOWER(%s) LIMIT 1",
                (f"%{title}%", f"%{title}%")
            )
            result = await cur.fetchone()
            return result[0] if result else None
    finally:
        await conn.close()

@router.get("/chat/history")
async def get_chat_history(req: Request, limit: int = Query(20, ge=1, le=100), anime_id: int | None = None):
    """Get chat history for this user (by IP), optionally filtered by anime_id"""
    user_ip = get_client_ip(req)
    conn = await psycopg.AsyncConnection.connect(settings.database_url)

    try:
        async with conn.cursor() as cur:
            if anime_id:
                # Filter by specific anime context
                await cur.execute("""
                    SELECT id, user_message, assistant_response, anime_context_id, anime_references, created_at
                    FROM chat_history
                    WHERE user_ip = %s AND anime_context_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (user_ip, anime_id, limit))
            else:
                # General chat history (no anime context)
                await cur.execute("""
                    SELECT id, user_message, assistant_response, anime_context_id, anime_references, created_at
                    FROM chat_history
                    WHERE user_ip = %s AND anime_context_id IS NULL
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (user_ip, limit))

            rows = await cur.fetchall()
            result = []
            for r in rows:
                anime_refs = []
                if r[4]:  # anime_references column
                    try:
                        refs_data = json.loads(r[4]) if isinstance(r[4], str) else r[4]
                        anime_refs = [AnimeReference(title=ref.get('title', ''), id=ref.get('id', 0)) for ref in refs_data]
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.warning(f"Bad anime_references for chat row {r[0]}: {e}")

                result.append(ChatHistoryItem(
                    id=r[0],
                    user_message=r[1],
                    assistant_response=r[2],
                    anime_context_id=r[3],
                    anime_references=anime_refs,
                    created_at=str(r[5])
                ))
            return result
    finally:
        await conn.close()

class AnimeSearchResult(BaseModel):
    id: int
    title_english: str
    title: str
    rating: float
    year: int
    genres: list
    cover_image: str
    relevance_score: float

def calculate_similarity(title: str, query: str) -> float:
    """Calculate fuzzy similarity score"""
    t = title.lower()
    q = query.lower()

    # Exact match
    if t == q:
        return 100

    # Starts with
    if t.startswith(q):
        return 80

    # Substring match
    if q in t:
        return 60

    # Word boundary (split by space, punctuation)
    words = re.split(r'[\s;:\-.,()]+', t)
    if q in words:
        return 75
    if any(w.startswith(q) for w in words):
        return 65

    # Fuzzy: chars in order
    matches = 0
    q_idx = 0
    for i in range(len(t)):
        if q_idx < len(q) and t[i] == q[q_idx]:
            matches += 1
            q_idx += 1

    if q_idx == len(q):
        return max(40, (matches / len(t)) * 50)

    return 0

@router.get("/search/anime")
async def search_anime(q: str = Query("", min_length=1), limit: int = Query(10, ge=1, le=50)):
    """Search anime by title, genres, or year"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)

    try:
        async with conn.cursor() as cur:
            # Get all anime (we'll score on backend)
            await cur.execute("""
                SELECT id, title_english, title, rating, year, genres, cover_image
                FROM anime
                ORDER BY rating DESC
                LIMIT 200
            """)

            rows = await cur.fetchall()
            results = []

            for row in rows:
                anime_id, title_eng, title_jp, rating, year, genres, cover = row

                # Calculate relevance score
                title_score = calculate_similarity(title_eng or title_jp or "", q)
                year_score = 30 if str(year) == q else 0
                genre_score = 30 if genres and any(g.lower().startswith(q.lower()) for g in genres) else 0

                total_score = max(title_score, year_score, genre_score)

                # Include if any match
                if total_score > 0:
                    results.append({
                        'anime': AnimeSearchResult(
                            id=anime_id,
                            title_english=title_eng or "",
                            title=title_jp or "",
                            rating=float(rating or 0),
                            year=year or 0,
                            genres=genres or [],
                            cover_image=cover or "",
                            relevance_score=total_score
                        ),
                        'score': total_score
                    })

            # Sort by score and return top results
            results.sort(key=lambda x: x['score'], reverse=True)
            return [r['anime'] for r in results[:limit]]
    finally:
        await conn.close()
