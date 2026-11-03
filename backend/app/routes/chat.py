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

class ChatResponse(BaseModel):
    response: str
    anime_ids: list[int] = []

class ChatHistoryItem(BaseModel):
    id: int
    user_message: str
    assistant_response: str
    anime_context_id: Optional[int]
    created_at: str

def get_client_ip(request: Request) -> str:
    """Extract client IP from request headers"""
    if request.client:
        return request.client.host
    return request.headers.get("x-forwarded-for", "unknown").split(",")[0].strip()

async def save_chat_message(user_ip: str, user_msg: str, assistant_msg: str, anime_id: Optional[int] = None):
    """Save chat message to database"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)
    try:
        async with conn.cursor() as cur:
            await cur.execute("""
                INSERT INTO chat_history (user_ip, user_message, assistant_response, anime_context_id)
                VALUES (%s, %s, %s, %s)
            """, (user_ip, user_msg, assistant_msg, anime_id))
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
            "content": "You are an anime expert with access to a database of 250+ anime. When the user asks about anime, use database results if provided. Be helpful and specific."
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

    # Save to chat history (fire and forget)
    user_ip = get_client_ip(req)
    await save_chat_message(user_ip, request.message, response_text, request.anime_id)

    return ChatResponse(response=response_text, anime_ids=[])

@router.get("/chat/history")
async def get_chat_history(req: Request, limit: int = Query(20, ge=1, le=100)):
    """Get chat history for this user (by IP)"""
    user_ip = get_client_ip(req)
    conn = await psycopg.AsyncConnection.connect(settings.database_url)

    try:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT id, user_message, assistant_response, anime_context_id, created_at
                FROM chat_history
                WHERE user_ip = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (user_ip, limit))

            rows = await cur.fetchall()
            return [
                ChatHistoryItem(
                    id=r[0],
                    user_message=r[1],
                    assistant_response=r[2],
                    anime_context_id=r[3],
                    created_at=str(r[4])
                )
                for r in rows
            ]
    finally:
        await conn.close()
