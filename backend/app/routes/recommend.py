from fastapi import APIRouter
from pydantic import BaseModel
from openai import OpenAI
import psycopg
from app.config import settings
import json

router = APIRouter(prefix="/api", tags=["recommendations"])

client = OpenAI(
    api_key=settings.openrouter_api_key,
    base_url="https://openrouter.ai/api/v1"
)

class RecommendRequest(BaseModel):
    preferences: str
    count: int = 5

@router.post("/recommend")
async def recommend_anime(request: RecommendRequest):
    """Get anime recommendations based on preferences"""

    # Search database for anime matching preferences
    conn = await psycopg.AsyncConnection.connect(settings.database_url)
    try:
        async with conn.cursor() as cur:
            # Search for anime with keywords from preferences
            await cur.execute("""
                SELECT a.id, a.title, a.rating, a.genres, a.plot
                FROM anime a
                WHERE a.title ILIKE %s OR a.plot ILIKE %s OR a.genres && %s
                ORDER BY a.rating DESC
                LIMIT 30
            """, (f"%{request.preferences}%", f"%{request.preferences}%", [request.preferences]))

            candidates = await cur.fetchall()
    finally:
        await conn.close()

    if not candidates:
        return {"error": "No anime found matching preferences"}

    # Format candidates for Claude
    candidates_text = "\n".join([
        f"- {row[1]} (Rating: {row[2]}, Genres: {', '.join(row[3])})"
        for row in candidates[:20]
    ])

    # Ask Claude to select best matches
    response = client.chat.completions.create(
        model=settings.model_name,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""User preferences: {request.preferences}

Available anime:
{candidates_text}

Select the top {request.count} best matches for these preferences.
Return ONLY a JSON array with this format (no other text):
[{{"anime_id": <id>, "title": "<title>", "reason": "<why this matches>"}}]"""
            }
        ]
    )

    try:
        text = response.choices[0].message.content.strip()
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
    except Exception as e:
        return {"error": f"Failed to parse recommendations: {str(e)}"}

    return {"error": "Could not generate recommendations"}
