"""The Explore similarity graph.

One endpoint ships the whole graph — 2,500 nodes and 20,000 edges is smaller
than the catalogue Explore already downloads — so re-centring on a click is a
walk in memory rather than a request.
"""
import logging

import psycopg
from fastapi import APIRouter, HTTPException, Query, Request

from app.config import settings
from app.utils.analytics import client_id, track

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/graph", tags=["graph"])

# Of the nearest-neighbour edges leaving the 8.5+ tier, only 17% land back
# inside it: most of what a great anime is closest to is not itself great. So
# the opening view needs edges computed *within* the sample, or it renders as
# scattered dots. The true neighbours show up in the detail panel instead.
SEED_EDGES_PER_NODE = 4


@router.get("")
async def get_graph(
    req: Request,
    seed_size: int = Query(120, ge=10, le=400),
    collapse_franchises: bool = Query(True),
):
    """Every node and edge, plus the opening sample to render first."""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)
    try:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT a.id, COALESCE(a.title_english, a.title), a.rating, a.year,
                       COALESCE(a.cover_image, ''), a.franchise_id, a.genres
                FROM anime a
                ORDER BY a.id;
            """)
            nodes = [
                {"id": r[0], "name": r[1], "rating": r[2], "year": r[3],
                 "cover": r[4], "franchise": r[5], "genres": list(r[6] or [])}
                for r in await cur.fetchall()
            ]

            await cur.execute("""
                SELECT anime_id, neighbour_id, round(similarity::numeric, 3)
                FROM anime_neighbours ORDER BY anime_id, rank;
            """)
            edges = [{"a": r[0], "b": r[1], "w": float(r[2])} for r in await cur.fetchall()]

            # The opening sample: the best-rated titles, one per franchise.
            # Sized by count rather than a rating cut, so the map is the same
            # size here as it is after travelling — a rating line gives 73
            # nodes at 8.5 and 139 at 8.3, and the view would change size.
            pick = (
                "SELECT id FROM (SELECT DISTINCT ON (franchise_id) id, rating FROM anime "
                "WHERE rating IS NOT NULL ORDER BY franchise_id, rating DESC, id) f "
                "ORDER BY rating DESC LIMIT %s"
                if collapse_franchises
                else "SELECT id FROM anime WHERE rating IS NOT NULL ORDER BY rating DESC LIMIT %s"
            )
            await cur.execute(f"""
                WITH sample AS ({pick}),
                emb AS (
                    SELECT s.id, e.plot_embedding
                    FROM sample s JOIN embeddings e ON e.anime_id = s.id
                )
                SELECT e1.id, n.id, round((1 - n.d)::numeric, 3)
                FROM emb e1
                CROSS JOIN LATERAL (
                    SELECT e2.id, e1.plot_embedding <=> e2.plot_embedding AS d
                    FROM emb e2 WHERE e2.id <> e1.id
                    ORDER BY e1.plot_embedding <=> e2.plot_embedding
                    LIMIT %s
                ) n;
            """, (seed_size, SEED_EDGES_PER_NODE))  # noqa: S608 - pick is one of two literals above
            seed_edges = [{"a": r[0], "b": r[1], "w": float(r[2])} for r in await cur.fetchall()]
            seed_ids = sorted({e["a"] for e in seed_edges})

            track(
                client_id(req), "graph_loaded",
                nodes=len(nodes), edges=len(edges),
                seed_nodes=len(seed_ids), collapsed=collapse_franchises,
            )
            return {
                "nodes": nodes,
                "edges": edges,
                "seed": {"ids": seed_ids, "edges": seed_edges, "size": len(seed_ids)},
            }
    except Exception as e:
        logger.error(f"Error building the graph: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Graph unavailable") from e
    finally:
        await conn.close()
