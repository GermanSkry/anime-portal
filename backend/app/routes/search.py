from fastapi import APIRouter, Query
from pydantic import BaseModel
import psycopg
from app.config import settings
from app.utils.embeddings import generate_embedding
from typing import Optional

router = APIRouter(prefix="/api/search", tags=["search"])

class AnimeSearchResponse(BaseModel):
    id: int
    title: str
    rating: Optional[float]
    genres: list
    year: Optional[int]
    studios: list

class SemanticSearchResponse(BaseModel):
    id: int
    title: str
    plot: Optional[str]
    rating: Optional[float]
    similarity: float
    genres: list

@router.get("")
async def search_anime(
    q: str = Query(..., min_length=1),
    genres: str = Query(None),
    year_min: int = Query(None),
    year_max: int = Query(None),
    studios: str = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Full-text search + multi-filter for anime"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)

    try:
        async with conn.cursor() as cur:
            query = """
                SELECT a.id, a.title, a.rating, a.genres, a.year,
                       COALESCE(array_agg(s.name) FILTER (WHERE s.name IS NOT NULL), '{}') as studios
                FROM anime a
                LEFT JOIN anime_studios asas ON a.id = asas.anime_id
                LEFT JOIN studios s ON asas.studio_id = s.id
                WHERE 1=1
            """
            params = []

            # Full-text search on title + plot
            if q:
                query += " AND (a.title ILIKE %s OR a.plot ILIKE %s)"
                search_term = f"%{q}%"
                params.extend([search_term, search_term])

            # Genre filter (array overlap)
            if genres:
                genre_list = [g.strip() for g in genres.split(",")]
                query += " AND a.genres && %s"
                params.append(genre_list)

            # Year range
            if year_min is not None:
                query += " AND a.year >= %s"
                params.append(year_min)
            if year_max is not None:
                query += " AND a.year <= %s"
                params.append(year_max)

            # Studio filter
            if studios:
                studio_list = [s.strip() for s in studios.split(",")]
                query += " AND s.name ILIKE ANY(%s)"
                params.append([f"%{st}%" for st in studio_list])

            query += """
                GROUP BY a.id, a.title, a.rating, a.genres, a.year
                ORDER BY a.rating DESC NULLS LAST
                LIMIT %s OFFSET %s
            """
            params.extend([limit, offset])

            await cur.execute(query, params)
            results = await cur.fetchall()

            return [
                AnimeSearchResponse(
                    id=r[0],
                    title=r[1],
                    rating=r[2],
                    genres=r[3] or [],
                    year=r[4],
                    studios=list(r[5]) if r[5] else []
                )
                for r in results
            ]
    finally:
        await conn.close()

@router.post("/semantic")
async def semantic_search(query_text: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=50)):
    """Find anime by semantic similarity to query"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)

    try:
        # Generate embedding for query
        query_embedding = await generate_embedding(query_text)
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        async with conn.cursor() as cur:
            # pgvector cosine similarity search
            await cur.execute(f"""
                SELECT a.id, a.title, a.plot, a.rating, a.genres,
                       1 - (e.plot_embedding <=> %s::vector) as similarity
                FROM embeddings e
                JOIN anime a ON e.anime_id = a.id
                ORDER BY similarity DESC
                LIMIT %s
            """, (embedding_str, limit))

            results = await cur.fetchall()

            return [
                SemanticSearchResponse(
                    id=r[0],
                    title=r[1],
                    plot=r[2][:200] if r[2] else None,
                    rating=r[3],
                    similarity=float(r[5]),
                    genres=r[4] or []
                )
                for r in results
            ]
    finally:
        await conn.close()
