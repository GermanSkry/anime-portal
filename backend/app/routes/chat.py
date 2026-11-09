"""Chat endpoint with Claude agent + chat history"""
from fastapi import APIRouter, Request, Query
from pydantic import BaseModel
from typing import Optional
from app.utils.claude_agent import chat_with_claude
import psycopg
from app.config import settings

router = APIRouter(prefix="/api", tags=["chat"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[list[ChatMessage]] = None
    anime_id: Optional[int] = None

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
    anime_context_id: Optional[int]
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

async def save_chat_message(user_ip: str, user_msg: str, assistant_msg: str, anime_id: Optional[int] = None, anime_references: list[AnimeReference] = None):
    """Save chat message to database"""
    import json

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
        print(f"Error saving chat: {e}")
    finally:
        await conn.close()

@router.post("/chat")
async def chat(request: ChatRequest, req: Request) -> ChatResponse:
    """Chat with Claude about anime. Augments with database search results."""
    messages = [
        {
            "role": "system",
            "content": """You are a concise anime recommendation assistant. Keep responses SHORT and direct (2-3 sentences max).

When recommending anime:
- List 3-5 titles max with brief 1-line descriptions
- Format: "**Title** - short description"
- Be conversational but brief
- Use database results when provided
- For trending/upcoming: search web and mention release info if available

Never write long paragraphs. Keep it punchy and actionable."""
        }
    ]

    if request.history:
        messages.extend([
            {"role": m.role, "content": m.content}
            for m in request.history
        ])

    messages.append({
        "role": "user",
        "content": request.message
    })

    response_text = await chat_with_claude(messages)

    # Extract anime references from response
    anime_references = await extract_anime_references(response_text)

    # Save to chat history (fire and forget)
    user_ip = get_client_ip(req)
    await save_chat_message(user_ip, request.message, response_text, request.anime_id, anime_references)

    return ChatResponse(
        response=response_text,
        anime_ids=[ref.id for ref in anime_references],
        anime_references=anime_references
    )

@router.get("/chat/history")
async def get_chat_history(req: Request, limit: int = Query(20, ge=1, le=100), anime_id: int = None):
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
                    import json
                    try:
                        refs_data = json.loads(r[4]) if isinstance(r[4], str) else r[4]
                        anime_refs = [AnimeReference(title=ref.get('title', ''), id=ref.get('id', 0)) for ref in refs_data]
                    except:
                        pass

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
