
import psycopg
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/anime", tags=["characters"])

class CharacterResponse(BaseModel):
    id: int
    name: str
    role: str
    image_url: str | None

@router.get("/{anime_id}/characters")
async def get_anime_characters(anime_id: int):
    """Get characters in an anime"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)

    try:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT c.id, c.name, ac.role_type, c.image_url
                FROM anime_characters ac
                JOIN characters c ON ac.character_id = c.id
                WHERE ac.anime_id = (
                    SELECT id FROM anime WHERE id = %s
                )
                ORDER BY ac.role_type DESC;
            """, (anime_id,))

            results = await cur.fetchall()
            return [
                {
                    "id": r[0],
                    "name": r[1],
                    "role": r[2],
                    "image_url": r[3]
                }
                for r in results
            ]
    finally:
        await conn.close()

