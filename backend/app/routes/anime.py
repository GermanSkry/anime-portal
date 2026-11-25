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
async def get_similar_anime(anime_id: int, limit: int = Query(5, ge=1, le=20)):
    """The nearest titles by plot, the same list the Explore graph draws.

    This used to score genre overlap, rating, year and studio in SQL. Two
    places then disagreed about what "similar" meant — a title page and the
    graph panel for the same anime listed different anime — so both now read
    anime_neighbours, which the ingest fills from the plot embeddings.

    Sequels are left out: the embedding puts Kaguya season 2 next to seasons
    1 and 3, which the reader can see for themselves. Only 8 neighbours are
    stored per title, so a long franchise can return fewer than `limit`.
    """
    try:
        conn = await psycopg.AsyncConnection.connect(settings.database_url)

        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    WITH near AS (
                        -- the table holds both directions of a mutual edge
                        SELECT DISTINCT ON (neighbour_id) neighbour_id, similarity
                        FROM anime_neighbours
                        WHERE anime_id = %s
                        ORDER BY neighbour_id, similarity DESC
                    ),
                    candidates AS (
                    """ + ANIME_COLUMNS + """
                        WHERE a.id IN (SELECT neighbour_id FROM near)
                          AND a.franchise_id IS DISTINCT FROM
                              (SELECT franchise_id FROM anime WHERE id = %s)
                    """ + ANIME_GROUP_BY + """
                    )
                    SELECT c.*, n.similarity
                    FROM candidates c JOIN near n ON n.neighbour_id = c.id
                    ORDER BY n.similarity DESC
                    LIMIT %s
                    """,  # noqa: S608 - the concatenated parts are module constants, never request data
                    (anime_id, anime_id, limit),
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
                        "synopsis": a[8] or "",
                        "similarity": float(a[10]),
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


@router.get("/{anime_id}/related")
async def get_related_anime(anime_id: int, limit: int = Query(4, ge=1, le=20)):
    """The rest of this title's franchise, oldest first.

    The franchise, not the direct relations: Sound! Euphonium 3 links only to
    an entry outside the catalogue, so a one-hop query returned nothing for it
    while the connected component has four other titles. Watch order is what
    the reader wants here, so it sorts by year rather than by rating.

    This route used to be registered twice — a one-hop version in
    characters.py, which won, and a deprecated alias for /similar here, which
    was unreachable. One route now.
    """
    try:
        conn = await psycopg.AsyncConnection.connect(settings.database_url)

        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    ANIME_COLUMNS + """
                    WHERE a.id <> %s
                      AND a.franchise_id = (SELECT franchise_id FROM anime WHERE id = %s)
                    """ + ANIME_GROUP_BY + """
                    ORDER BY a.year NULLS LAST, a.id
                    LIMIT %s
                    """,  # noqa: S608 - the concatenated parts are module constants, never request data
                    (anime_id, anime_id, limit),
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
                        "synopsis": a[8] or "",
                    }
                    for a in await cur.fetchall()
                ]
        finally:
            await conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding the franchise: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Anime database unavailable") from e

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
