from fastapi import APIRouter, Query
from pydantic import BaseModel
import psycopg
from app.config import settings
from typing import Optional

router = APIRouter(prefix="/api/anime", tags=["anime"])

class AnimeResponse(BaseModel):
    id: int
    title: str
    title_english: Optional[str]
    year: Optional[int]
    rating: Optional[float]
    genres: list
    studios: list
    cover_image: Optional[str]

@router.get("", response_model=list[AnimeResponse])
async def get_anime(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("rating", regex="^(rating|year|title)$")
):
    """Get anime list with pagination"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)

    try:
        async with conn.cursor() as cur:
            order_by = {
                "rating": "rating DESC",
                "year": "year DESC",
                "title": "title ASC"
            }.get(sort_by, "rating DESC")

            # Get anime with studios (joined from anime_studios table)
            await cur.execute(
                f"""
                SELECT a.id, a.title, a.title_english, a.year, a.rating, a.genres, a.cover_image,
                       COALESCE(array_agg(s.name) FILTER (WHERE s.name IS NOT NULL), '{{}}') as studios
                FROM anime a
                LEFT JOIN anime_studios asas ON a.id = asas.anime_id
                LEFT JOIN studios s ON asas.studio_id = s.id
                GROUP BY a.id, a.title, a.title_english, a.year, a.rating, a.genres, a.cover_image
                ORDER BY {order_by}
                LIMIT %s OFFSET %s;
                """,
                (limit, offset)
            )
            results = await cur.fetchall()

            return [
                AnimeResponse(
                    id=r[0],
                    title=r[1],
                    title_english=r[2],
                    year=r[3],
                    rating=r[4],
                    genres=r[5] or [],
                    studios=list(r[7]) if r[7] else [],
                    cover_image=r[6]
                )
                for r in results
            ]
    finally:
        await conn.close()

@router.get("/{anime_id}", response_model=AnimeResponse)
async def get_anime_by_id(anime_id: int):
    """Get single anime by ID"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)

    try:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT a.id, a.title, a.title_english, a.year, a.rating, a.genres, a.cover_image,
                       COALESCE(array_agg(s.name) FILTER (WHERE s.name IS NOT NULL), '{}') as studios
                FROM anime a
                LEFT JOIN anime_studios asas ON a.id = asas.anime_id
                LEFT JOIN studios s ON asas.studio_id = s.id
                WHERE a.id = %s
                GROUP BY a.id, a.title, a.title_english, a.year, a.rating, a.genres, a.cover_image;
                """,
                (anime_id,)
            )
            result = await cur.fetchone()

            if not result:
                return {"error": "Anime not found"}

            return AnimeResponse(
                id=result[0],
                title=result[1],
                title_english=result[2],
                year=result[3],
                rating=result[4],
                genres=result[5] or [],
                studios=list(result[7]) if result[7] else [],
                cover_image=result[6]
            )
    finally:
        await conn.close()

@router.get("/stats/count")
async def get_anime_count():
    """Get total anime count (useful for pagination)"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)

    try:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM anime;")
            count = (await cur.fetchone())[0]
            return {"count": count}
    finally:
        await conn.close()
