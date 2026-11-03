from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
import psycopg
from app.config import settings
from typing import Optional
import logging
import re

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/anime", tags=["anime"])

def clean_title(title: str) -> str:
    """Clean up anime titles by removing trailing dashes and extra punctuation"""
    if not title:
        return title
    # Remove trailing dashes and spaces
    title = re.sub(r'\s*-\s*$', '', title).strip()
    return title

class AnimeResponse(BaseModel):
    id: int
    title: str
    title_english: Optional[str] = None
    year: Optional[int]
    rating: Optional[float]
    genres: list = Field(default_factory=list)
    studios: list = Field(default_factory=list)
    cover_image: Optional[str] = None
    trailer_url: Optional[str] = None
    synopsis: Optional[str] = None

    def dict(self, **kwargs):
        """Custom dict to use 'name' as alias for 'title' in JSON"""
        d = super().dict(**kwargs)
        d['name'] = d.pop('title')
        return d

# Mock data - returns both title (for API) and name (for frontend compatibility)
MOCK_ANIME_RAW = [
    {"id": 1, "title": "Steins;Gate", "name": "Steins;Gate", "year": 2011, "rating": 9.0, "genres": ["Sci-Fi", "Thriller"], "genre": "Sci-Fi", "studios": ["White Fox"], "studio": "White Fox"},
    {"id": 2, "title": "Attack on Titan", "name": "Attack on Titan", "year": 2013, "rating": 8.9, "genres": ["Action", "Dark Fantasy"], "genre": "Action", "studios": ["Wit Studio"], "studio": "Wit Studio"},
    {"id": 3, "title": "Demon Slayer", "name": "Demon Slayer", "year": 2019, "rating": 8.8, "genres": ["Action", "Adventure"], "genre": "Action", "studios": ["ufotable"], "studio": "ufotable"},
    {"id": 4, "title": "Jujutsu Kaisen", "name": "Jujutsu Kaisen", "year": 2020, "rating": 8.7, "genres": ["Action", "Supernatural"], "genre": "Action", "studios": ["MAPPA"], "studio": "MAPPA"},
    {"id": 5, "title": "Code Geass", "name": "Code Geass", "year": 2006, "rating": 8.6, "genres": ["Action", "Mecha"], "genre": "Action", "studios": ["Sunrise"], "studio": "Sunrise"},
]

MOCK_ANIME = [
    AnimeResponse(
        id=a["id"], title=a["title"], title_english=a.get("title_english", a["name"]),
        year=a["year"], rating=a["rating"], genres=a["genres"],
        studios=a["studios"], cover_image="https://via.placeholder.com/300x400"
    )
    for a in MOCK_ANIME_RAW
]

@router.get("/debug/db-check")
async def debug_db():
    """Debug: Check database connection and data"""
    try:
        conn = await psycopg.AsyncConnection.connect(settings.database_url)
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM anime;")
            count = await cur.fetchone()

            await cur.execute("SELECT id, title, cover_image FROM anime LIMIT 1;")
            row = await cur.fetchone()

            await conn.close()

            return {
                "status": "✓ Connected",
                "total_anime": count[0] if count else 0,
                "sample": {
                    "id": row[0],
                    "title": row[1],
                    "cover_image": row[2][:80] if row[2] else "EMPTY"
                }
            }
    except Exception as e:
        return {"status": f"✗ Error: {e}"}

@router.get("")
async def get_anime(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("rating", regex="^(rating|year|title)$")
):
    """Get anime list with pagination"""
    try:
        conn = await psycopg.AsyncConnection.connect(settings.database_url)

        try:
            async with conn.cursor() as cur:
                order_by = {
                    "rating": "rating DESC",
                    "year": "year DESC",
                    "title": "title ASC"
                }.get(sort_by, "rating DESC")

                # Query only columns that exist in the table
                await cur.execute(
                    f"""
                    SELECT id, title, title_english, year, rating, genres, cover_image, studios, plot, trailer_url
                    FROM anime
                    ORDER BY {order_by}
                    LIMIT %s OFFSET %s;
                    """,
                    (limit, offset)
                )
                results = await cur.fetchall()

                if results:
                    return [
                        {
                            "id": r[0],
                            "name": clean_title(r[1]),  # Return as 'name' for frontend
                            "title_english": clean_title(r[2]) if r[2] else None,
                            "year": r[3],
                            "rating": r[4],
                            "genres": list(r[5]) if r[5] else [],
                            "cover_image": r[6] or "",
                            "trailer_url": r[9] if r[9] else None,
                            "studios": list(r[7]) if r[7] else [],
                            "synopsis": r[8] or ""
                        }
                        for r in results
                    ]
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Database error in get_anime: {e}", exc_info=True)
        print(f"⚠️ DATABASE ERROR: {e}")  # Debug print
        import traceback
        traceback.print_exc()

    return MOCK_ANIME[offset:offset+limit]

@router.get("/debug/db-check")
async def debug_db():
    """Debug: Check database connection and data"""
    try:
        conn = await psycopg.AsyncConnection.connect(settings.database_url)
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM anime;")
            count = await cur.fetchone()

            await cur.execute("SELECT id, title, cover_image FROM anime LIMIT 1;")
            row = await cur.fetchone()

            await conn.close()

            return {
                "status": "✓ Connected",
                "total_anime": count[0] if count else 0,
                "sample": {
                    "id": row[0],
                    "title": row[1],
                    "cover_image": row[2][:80] if row[2] else "EMPTY"
                }
            }
    except Exception as e:
        return {"status": f"✗ Error: {e}"}

@router.get("/{anime_id}/similar")
async def get_similar_anime(anime_id: int, limit: int = Query(4, ge=1, le=20), min_rating: float = Query(0, ge=0, le=10)):
    """Get similar anime based on genre, rating, year, and studio"""
    try:
        conn = await psycopg.AsyncConnection.connect(settings.database_url)

        try:
            async with conn.cursor() as cur:
                # Get the target anime
                await cur.execute(
                    "SELECT id, title, title_english, year, rating, genres, cover_image, studios, plot FROM anime WHERE id = %s;",
                    (anime_id,)
                )
                target = await cur.fetchone()

                if not target:
                    return []

                # Get all anime except the target
                await cur.execute(
                    "SELECT id, title, title_english, year, rating, genres, cover_image, studios, plot, trailer_url FROM anime WHERE id != %s;",
                    (anime_id,)
                )
                all_anime = await cur.fetchall()

                # Score each anime based on similarity
                scored = []
                target_genres = set(target[5]) if target[5] else set()
                target_rating = target[4] or 0
                target_year = target[3] or 0
                target_studios = set(target[7]) if target[7] else set()

                for anime in all_anime:
                    score = 0

                    # Genre match (max 50 points)
                    anime_genres = set(anime[5]) if anime[5] else set()
                    genre_overlap = len(target_genres & anime_genres)
                    if target_genres:
                        score += (genre_overlap / len(target_genres)) * 50

                    # Rating proximity (max 30 points)
                    rating_diff = abs(anime[4] or 0 - target_rating)
                    score += max(0, 30 - (rating_diff * 3))

                    # Year proximity (max 15 points)
                    year_diff = abs(anime[3] or 0 - target_year)
                    score += max(0, 15 - (year_diff * 0.5))

                    # Studio match (max 5 points)
                    anime_studios = set(anime[7]) if anime[7] else set()
                    if target_studios & anime_studios:
                        score += 5

                    scored.append((score, anime))

                # Sort by score (descending) and fetch more to allow filtering
                scored.sort(key=lambda x: x[0], reverse=True)

                # Get top candidates (fetch more to allow filtering)
                candidates = [anime for _, anime in scored[:limit * 3]]

                # Filter by min_rating if specified, but keep at least 'limit' results
                high_rated = [a for a in candidates if (a[4] or 0) >= min_rating]
                similar = high_rated if len(high_rated) >= limit else candidates

                # Sort by rating (descending) and take top results
                similar.sort(key=lambda x: x[4] or 0, reverse=True)
                similar = similar[:limit]

                # Format response
                return [
                    {
                        "id": a[0],
                        "name": clean_title(a[1]),
                        "title_english": clean_title(a[2]) if a[2] else None,
                        "year": a[3],
                        "rating": a[4],
                        "genres": list(a[5]) if a[5] else [],
                        "cover_image": a[6] or "",
                        "trailer_url": a[9] if a[9] else None,
                        "studios": list(a[7]) if a[7] else [],
                        "synopsis": a[8] or ""
                    }
                    for a in similar
                ]
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Error finding similar anime: {e}")
        return []

@router.get("/{anime_id}/related")
async def get_related_anime(anime_id: int, limit: int = Query(4, ge=1, le=20)):
    """Get related/similar anime (deprecated - use /similar)"""
    return await get_similar_anime(anime_id, limit)

@router.get("/{anime_id}")
async def get_anime_by_id(anime_id: int):
    """Get single anime by ID"""
    try:
        conn = await psycopg.AsyncConnection.connect(settings.database_url)

        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id, title, title_english, year, rating, genres, cover_image, studios, plot, trailer_url
                    FROM anime
                    WHERE id = %s;
                    """,
                    (anime_id,)
                )
                result = await cur.fetchone()

                if result:
                    return {
                        "id": result[0],
                        "name": clean_title(result[1]),
                        "title_english": clean_title(result[2]) if result[2] else None,
                        "year": result[3],
                        "rating": result[4],
                        "genres": list(result[5]) if result[5] else [],
                        "cover_image": result[6] or "",
                        "trailer_url": result[9] if result[9] else None,
                        "studios": list(result[7]) if result[7] else [],
                        "synopsis": result[8] or ""
                    }
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Database error in get_anime_by_id: {e}")

    for anime in MOCK_ANIME:
        if anime.id == anime_id:
            return anime.dict()
    return MOCK_ANIME[0].dict()

@router.get("/stats/count")
async def get_anime_count():
    """Get total anime count"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)

    try:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM anime;")
            count = (await cur.fetchone())[0]
            return {"count": count}
    finally:
        await conn.close()
