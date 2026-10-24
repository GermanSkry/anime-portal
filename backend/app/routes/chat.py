"""Chat endpoint with Claude agent"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.utils.claude_agent import chat_with_claude

router = APIRouter(prefix="/api", tags=["chat"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[list[ChatMessage]] = None

class ChatResponse(BaseModel):
    response: str
    anime_ids: list[int] = []

@router.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
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
    return ChatResponse(response=response_text, anime_ids=[])
