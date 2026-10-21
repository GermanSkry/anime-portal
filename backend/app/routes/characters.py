from fastapi import APIRouter, Query
from pydantic import BaseModel
import psycopg
from app.config import settings
from typing import Optional

router = APIRouter(prefix="/api/anime", tags=["characters"])

class CharacterResponse(BaseModel):
    id: int
    name: str
    role: str
    image_url: Optional[str]

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

@router.get("/{anime_id}/related")
async def get_related_anime(
    anime_id: int,
    relationship_type: Optional[str] = Query(None, regex="^(SEQUEL|PREQUEL|SPIN_OFF|SIDE_STORY)$")
):
    """Get related anime (sequels, prequels, spin-offs)"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)

    try:
        async with conn.cursor() as cur:
            query = """
                SELECT a.id, a.title, a.cover_image, a.rating, ra.relationship_type
                FROM related_anime ra
                JOIN anime a ON ra.anime_id_to = a.id
                WHERE ra.anime_id_from = %s
            """
            params = [anime_id]

            if relationship_type:
                query += " AND ra.relationship_type = %s"
                params.append(relationship_type)

            query += " ORDER BY ra.relationship_type;"

            await cur.execute(query, params)
            results = await cur.fetchall()

            return [
                {
                    "id": r[0],
                    "title": r[1],
                    "cover_image": r[2],
                    "rating": r[3],
                    "relationship_type": r[4]
                }
                for r in results
            ]
    finally:
        await conn.close()
