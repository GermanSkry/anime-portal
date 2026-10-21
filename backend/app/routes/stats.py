from fastapi import APIRouter
import psycopg
from app.config import settings

router = APIRouter(prefix="/api/stats", tags=["stats"])

@router.get("/overview")
async def get_stats_overview():
    """Get dashboard statistics"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)

    try:
        async with conn.cursor() as cur:
            # Total anime count
            await cur.execute("SELECT COUNT(*) FROM anime;")
            total_anime = (await cur.fetchone())[0]

            # Average rating
            await cur.execute("SELECT AVG(rating) FROM anime WHERE rating > 0;")
            avg_rating = (await cur.fetchone())[0] or 0

            # Genre distribution
            await cur.execute("""
                SELECT unnest(genres) as genre, COUNT(*) as count
                FROM anime
                WHERE genres IS NOT NULL
                GROUP BY genre
                ORDER BY count DESC
                LIMIT 15;
            """)
            genres = await cur.fetchall()

            # Studios distribution
            await cur.execute("""
                SELECT s.name, COUNT(*) as count
                FROM anime_studios asa
                JOIN studios s ON asa.studio_id = s.id
                GROUP BY s.name
                ORDER BY count DESC
                LIMIT 10;
            """)
            studios = await cur.fetchall()

            # Year distribution
            await cur.execute("""
                SELECT year, COUNT(*) as count
                FROM anime
                WHERE year IS NOT NULL
                GROUP BY year
                ORDER BY year DESC
                LIMIT 30;
            """)
            years = await cur.fetchall()

            # Top rated
            await cur.execute("""
                SELECT id, title, rating, cover_image
                FROM anime
                WHERE rating > 0
                ORDER BY rating DESC
                LIMIT 10;
            """)
            top_rated = await cur.fetchall()

            # Most popular
            await cur.execute("""
                SELECT id, title, rating, cover_image
                FROM anime
                ORDER BY rating DESC
                LIMIT 10;
            """)
            popular = await cur.fetchall()

            return {
                "total_anime": total_anime,
                "average_rating": float(avg_rating),
                "genres_distribution": [
                    {"genre": g[0], "count": g[1]}
                    for g in genres
                ],
                "studios_distribution": [
                    {"studio": s[0], "count": s[1]}
                    for s in studios
                ],
                "year_distribution": [
                    {"year": y[0], "count": y[1]}
                    for y in years
                ],
                "top_rated": [
                    {"id": t[0], "title": t[1], "rating": t[2], "cover_image": t[3]}
                    for t in top_rated
                ],
                "popular": [
                    {"id": p[0], "title": p[1], "rating": p[2], "cover_image": p[3]}
                    for p in popular
                ]
            }
    finally:
        await conn.close()

@router.get("/count")
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

@router.get("/by-year")
async def get_anime_by_year():
    """Get anime distribution by year"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)

    try:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT year, COUNT(*) as count
                FROM anime
                WHERE year IS NOT NULL
                GROUP BY year
                ORDER BY year DESC;
            """)
            results = await cur.fetchall()
            return [{"year": r[0], "count": r[1]} for r in results]
    finally:
        await conn.close()

@router.get("/by-genre")
async def get_anime_by_genre():
    """Get anime distribution by genre"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)

    try:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT unnest(genres) as genre, COUNT(*) as count
                FROM anime
                WHERE genres IS NOT NULL AND genres != '{}'
                GROUP BY genre
                ORDER BY count DESC;
            """)
            results = await cur.fetchall()
            return [{"genre": r[0], "count": r[1]} for r in results]
    finally:
        await conn.close()
