import logging
import re

import psycopg
from fastapi import APIRouter, HTTPException, Query

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/anime", tags=["anime"])

def clean_title(title: str) -> str:
    """Clean up anime titles by removing trailing dashes and extra punctuation"""
    if not title:
        return title
    # Remove trailing dashes and spaces
    title = re.sub(r'\s*-\s*$', '', title).strip()
    return title

# The anime table has no studios column: studios live in studios + anime_studios.
# Every query below shares this projection so the row layout stays identical.
ANIME_COLUMNS = """
    SELECT a.id, a.title, a.title_english, a.year, a.rating, a.genres, a.cover_image,
           COALESCE(array_agg(s.name) FILTER (WHERE s.name IS NOT NULL), '{}') AS studios,
           a.plot, a.trailer_url
    FROM anime a
    LEFT JOIN anime_studios ast ON a.id = ast.anime_id
    LEFT JOIN studios s ON ast.studio_id = s.id
"""
ANIME_GROUP_BY = """
    GROUP BY a.id, a.title, a.title_english, a.year, a.rating, a.genres, a.cover_image, a.plot, a.trailer_url
"""

@router.get("/debug/db-check")
async def debug_db():
    """Debug: Check database connection and data"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)
    try:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM anime;")
            count = await cur.fetchone()

            await cur.execute("SELECT id, title, cover_image FROM anime LIMIT 1;")
            row = await cur.fetchone()

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
    finally:
        await conn.close()

@router.get("")
async def get_anime(
    limit: int = Query(10, ge=1, le=2500),  # the whole catalogue, for Explore's client-side filtering
    offset: int = Query(0, ge=0),
    sort_by: str = Query("rating", regex="^(rating|year|title)$")
):
    """Get anime list with pagination"""
    try:
        conn = await psycopg.AsyncConnection.connect(settings.database_url)

        try:
            async with conn.cursor() as cur:
                order_by = {
                    "rating": "a.rating DESC",
                    "year": "a.year DESC",
                    "title": "a.title ASC"
                }.get(sort_by, "a.rating DESC")

                await cur.execute(
                    ANIME_COLUMNS + ANIME_GROUP_BY + f" ORDER BY {order_by} LIMIT %s OFFSET %s;",
                    (limit, offset)
                )
                results = await cur.fetchall()

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
        raise HTTPException(status_code=503, detail="Anime database unavailable") from e

@router.get("/{anime_id}/similar")
async def get_similar_anime(anime_id: int, limit: int = Query(4, ge=1, le=20), min_rating: float = Query(0, ge=0, le=10)):
    """Get similar anime based on genre, rating, year, and studio"""
    try:
        conn = await psycopg.AsyncConnection.connect(settings.database_url)

        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT year, rating, genres FROM anime WHERE id = %s;", (anime_id,)
                )
                target = await cur.fetchone()
                if not target:
                    return []
                target_year, target_rating, target_genres = target[0] or 0, target[1] or 0, target[2] or []

                # Scored in SQL and limited there. Doing it in Python meant reading
                # the whole anime table on every title page view, which is fine at
                # 250 rows and not at a few thousand.
                #
                # The Python version also mis-scored: `abs(rating or 0 - target)`
                # parses as `abs(rating)`, because `or` binds looser than `-`. That
                # rewarded badly rated anime and made the year term always zero.
                await cur.execute(
                    """
                    WITH candidates AS (
                    """ + ANIME_COLUMNS + " WHERE a.id != %s " + ANIME_GROUP_BY + """
                    )
                    SELECT id, title, title_english, year, rating, genres, cover_image,
                           studios, plot, trailer_url
                    FROM candidates
                    ORDER BY
                        -- min_rating prefers rather than filters, so a title with few
                        -- good neighbours still fills its row
                        (COALESCE(rating, 0) >= %s) DESC,
                        (
                            CASE WHEN cardinality(%s::text[]) > 0
                                 THEN (SELECT count(*) FROM unnest(genres) g
                                       WHERE g = ANY(%s::text[]))::float
                                      / cardinality(%s::text[]) * 50
                                 ELSE 0 END
                            + GREATEST(0, 30 - ABS(COALESCE(rating, 0) - %s) * 3)
                            + GREATEST(0, 15 - ABS(COALESCE(year, 0) - %s) * 0.5)
                            -- array_agg over studios.name yields varchar[], not text[]
                            + CASE WHEN studios::text[] && %s::text[] THEN 5 ELSE 0 END
                        ) DESC,
                        rating DESC NULLS LAST
                    LIMIT %s
                    """,  # noqa: S608 - the concatenated parts are module constants, never request data
                    (anime_id, min_rating, target_genres, target_genres, target_genres,
                     target_rating, target_year, await _studios_of(cur, anime_id), limit),
                )

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
                    for a in await cur.fetchall()
                ]
        finally:
            await conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding similar anime: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Anime database unavailable") from e


async def _studios_of(cur, anime_id: int) -> list[str]:
    """The studio names for one anime, for the similarity studio bonus."""
    await cur.execute(
        """
        SELECT COALESCE(array_agg(s.name) FILTER (WHERE s.name IS NOT NULL), '{}')
        FROM anime_studios ast JOIN studios s ON ast.studio_id = s.id
        WHERE ast.anime_id = %s;
        """,
        (anime_id,),
    )
    row = await cur.fetchone()
    return list(row[0]) if row and row[0] else []


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
                    ANIME_COLUMNS + " WHERE a.id = %s" + ANIME_GROUP_BY,
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
                raise HTTPException(status_code=404, detail=f"Anime {anime_id} not found")
        finally:
            await conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error in get_anime_by_id: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Anime database unavailable") from e

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
