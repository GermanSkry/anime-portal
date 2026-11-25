#!/usr/bin/env python3
"""Ingest anime data into PostgreSQL with enhanced schema (Phase 1+2)"""
import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg

from app.config import settings
from app.utils.embeddings import generate_embedding

DATA_DIR = Path(__file__).parent.parent / "data"
ANIME_FILE = DATA_DIR / "anime.json"

# edges kept per title for the Explore graph
NEIGHBOURS_PER_ANIME = 8

async def ingest_anime():
    """Load anime data into database with enhanced schema"""
    if not ANIME_FILE.exists():
        print(f"❌ Data file not found: {ANIME_FILE}")
        print("   Run: python scripts/fetch_anime_enhanced.py")
        return

    print(f"📥 Loading anime from {ANIME_FILE}...")
    with open(ANIME_FILE) as f:
        anime_list = json.load(f)

    if not anime_list:
        print(f"❌ {ANIME_FILE} is empty — nothing to ingest.")
        print("   Regenerate it: python scripts/fetch_anime_enhanced.py")
        return

    print(f"   Loaded {len(anime_list)} anime")

    # Connect to database
    conn = await psycopg.AsyncConnection.connect(settings.database_url)

    try:
        async with conn.cursor() as cur:
            # Initialize DB schema
            print("🔧 Initializing database schema...")
            # required: /api/search/semantic queries plot_embedding with the pgvector `<=>` operator
            await cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

            # Main anime table (enhanced with trailers - Phase 1.5)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS anime (
                    id SERIAL PRIMARY KEY,
                    anilist_id INTEGER UNIQUE NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    title_english VARCHAR(255),
                    title_japanese VARCHAR(255),
                    year INTEGER,
                    season VARCHAR(20),
                    episodes INTEGER,
                    status VARCHAR(50),
                    rating FLOAT,
                    plot TEXT,
                    cover_image VARCHAR(255),
                    banner_image VARCHAR(255),
                    trailer_url VARCHAR(500),
                    genres TEXT[] DEFAULT '{}',
                    themes TEXT[] DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Studios table
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS studios (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    website VARCHAR(255)
                );
            """)

            # Anime-Studios relationship
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS anime_studios (
                    anime_id INTEGER REFERENCES anime(id) ON DELETE CASCADE,
                    studio_id INTEGER REFERENCES studios(id) ON DELETE CASCADE,
                    role VARCHAR(50) DEFAULT 'Animation',
                    PRIMARY KEY (anime_id, studio_id)
                );
            """)

            # Characters table
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    id SERIAL PRIMARY KEY,
                    anilist_char_id INTEGER UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    name_japanese VARCHAR(255),
                    role VARCHAR(100),
                    description TEXT,
                    image_url VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Anime-Characters relationship
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS anime_characters (
                    anime_id INTEGER REFERENCES anime(id) ON DELETE CASCADE,
                    character_id INTEGER REFERENCES characters(id) ON DELETE CASCADE,
                    role_type VARCHAR(50),
                    PRIMARY KEY (anime_id, character_id)
                );
            """)

            # Related anime (sequels, prequels, etc)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS related_anime (
                    id SERIAL PRIMARY KEY,
                    anime_id_from INTEGER REFERENCES anime(id) ON DELETE CASCADE,
                    anime_id_to INTEGER REFERENCES anime(id) ON DELETE CASCADE,
                    relationship_type VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Embeddings for semantic search; 384 dims = all-MiniLM-L6-v2, the model app/utils/embeddings.py loads.
            # Older databases have plot_embedding as TEXT, which CREATE IF NOT EXISTS would keep and which
            # silently breaks the `<=>` query in /api/search/semantic. Drop it only in that case — dropping
            # unconditionally would throw away every embedding on every run, which is the slow part.
            await cur.execute("""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'embeddings'
                          AND column_name = 'plot_embedding'
                          AND udt_name <> 'vector'
                    ) THEN
                        DROP TABLE embeddings;
                    END IF;
                END $$;
            """)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id SERIAL PRIMARY KEY,
                    anime_id INTEGER UNIQUE NOT NULL REFERENCES anime(id) ON DELETE CASCADE,
                    plot_embedding vector(384),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Recommendations table
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    id SERIAL PRIMARY KEY,
                    anime_id INTEGER REFERENCES anime(id) ON DELETE CASCADE,
                    recommended_anime_id INTEGER REFERENCES anime(id) ON DELETE CASCADE,
                    score FLOAT,
                    reason VARCHAR(255),
                    source VARCHAR(100) DEFAULT 'content',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Runtime tables. Nothing here is derived from anime.json, so the wipe below
            # leaves them alone. No foreign key to anime(id): re-ingesting replaces every
            # anime row, and that must not erase a user's chat or search history.
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id SERIAL PRIMARY KEY,
                    user_ip VARCHAR(45),
                    user_message TEXT NOT NULL,
                    assistant_response TEXT NOT NULL,
                    anime_context_id INTEGER,
                    anime_references JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await cur.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id SERIAL PRIMARY KEY,
                    query TEXT NOT NULL,
                    result_count INTEGER,
                    query_type VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # message_id is unique: the DB consumer reads it to skip messages Kafka redelivers
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS processed_messages (
                    id SERIAL PRIMARY KEY,
                    topic VARCHAR(100) NOT NULL,
                    message_id VARCHAR(100) NOT NULL UNIQUE,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # primary key doubles as the ON CONFLICT target the search indexer upserts on
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS search_engagement (
                    anime_id INTEGER NOT NULL,
                    engagement_type VARCHAR(50) NOT NULL,
                    count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (anime_id, engagement_type)
                );
            """)

            # Create indexes
            print("📑 Creating indexes...")
            await cur.execute("CREATE INDEX IF NOT EXISTS idx_anime_year ON anime(year);")
            await cur.execute("CREATE INDEX IF NOT EXISTS idx_anime_season ON anime(season);")
            await cur.execute("CREATE INDEX IF NOT EXISTS idx_anime_rating ON anime(rating DESC);")
            await cur.execute("CREATE INDEX IF NOT EXISTS idx_anime_genres ON anime USING GIN(genres);")
            await cur.execute("CREATE INDEX IF NOT EXISTS idx_related_from ON related_anime(anime_id_from);")
            await cur.execute("CREATE INDEX IF NOT EXISTS idx_recommendations ON recommendations(anime_id, score DESC);")
            await cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_history_user ON chat_history(user_ip, created_at DESC);")
            await cur.execute("CREATE INDEX IF NOT EXISTS idx_search_history_created ON search_history(created_at DESC);")

            # What is already here, so unchanged titles can be left alone. This used
            # to DELETE every table and rebuild, which renumbered every anime id on
            # each run — breaking bookmarked /title/<id> links and leaving
            # chat_history.anime_context_id pointing at the wrong title — and spent
            # minutes recomputing embeddings that had not changed.
            await cur.execute("""
                SELECT a.anilist_id, a.id, a.plot, (e.anime_id IS NOT NULL)
                FROM anime a LEFT JOIN embeddings e ON e.anime_id = a.id;
            """)
            existing = {r[0]: (r[1], r[2], r[3]) for r in await cur.fetchall()}
            print(f"📦 {len(existing)} titles already in the database")

            # Titles no longer in the file are left alone rather than deleted: a
            # fetch that legitimately returns a different popular 2500 should not
            # silently drop rows other tables may refer to.
            print("📝 Upserting anime...")
            embedded = skipped = 0
            for i, anime in enumerate(anime_list):
                try:
                    await cur.execute("""
                        INSERT INTO anime (
                            anilist_id, title, title_english, title_japanese,
                            year, season, episodes, status, rating, plot,
                            cover_image, banner_image, trailer_url, genres, themes
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (anilist_id) DO UPDATE SET
                            title = EXCLUDED.title,
                            title_english = EXCLUDED.title_english,
                            title_japanese = EXCLUDED.title_japanese,
                            year = EXCLUDED.year,
                            season = EXCLUDED.season,
                            episodes = EXCLUDED.episodes,
                            status = EXCLUDED.status,
                            rating = EXCLUDED.rating,
                            plot = EXCLUDED.plot,
                            cover_image = EXCLUDED.cover_image,
                            banner_image = EXCLUDED.banner_image,
                            trailer_url = EXCLUDED.trailer_url,
                            genres = EXCLUDED.genres,
                            themes = EXCLUDED.themes,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id;
                    """, (
                        anime["id"],
                        anime["title"],
                        anime.get("title_english"),
                        anime.get("title_japanese"),
                        anime.get("year"),
                        anime.get("season"),
                        anime.get("episodes"),
                        anime.get("status", "UNKNOWN"),
                        anime.get("rating"),
                        anime.get("plot"),
                        anime.get("cover_image"),
                        anime.get("banner_image"),
                        anime.get("trailer_url"),
                        anime.get("genres", []),
                        anime.get("themes", [])
                    ))

                    anime_db_id = (await cur.fetchone())[0]

                    # Insert studios
                    for studio_name in anime.get("studios", []):
                        await cur.execute("""
                            INSERT INTO studios (name) VALUES (%s)
                            ON CONFLICT (name) DO NOTHING
                            RETURNING id;
                        """, (studio_name,))

                        result = await cur.fetchone()
                        if result:
                            studio_id = result[0]
                        else:
                            # Get existing studio ID
                            await cur.execute("SELECT id FROM studios WHERE name = %s;", (studio_name,))
                            studio_id = (await cur.fetchone())[0]

                        await cur.execute("""
                            INSERT INTO anime_studios (anime_id, studio_id, role)
                            VALUES (%s, %s, 'Animation')
                            ON CONFLICT DO NOTHING;
                        """, (anime_db_id, studio_id))

                    # Embedding the plot is the slow step — 2500 of them is seconds
                    # on a GPU and many minutes on the VPS's CPU-only vCPU. Only
                    # redo it when the plot actually changed, or when none exists.
                    plot_text = anime.get("plot", "") or anime.get("title", "")
                    was = existing.get(anime["id"])
                    if was and was[2] and was[1] == anime.get("plot"):
                        skipped += 1
                        if (i + 1) % 500 == 0:
                            print(f"  Processed {i + 1}/{len(anime_list)}")
                        continue

                    embedding = await generate_embedding(plot_text)
                    embedded += 1
                    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

                    await cur.execute("""
                        INSERT INTO embeddings (anime_id, plot_embedding)
                        VALUES (%s, %s)
                        ON CONFLICT (anime_id) DO UPDATE
                            SET plot_embedding = EXCLUDED.plot_embedding;
                    """, (anime_db_id, embedding_str))

                    if (i + 1) % 50 == 0:
                        print(f"  Processed {i + 1}/{len(anime_list)}")
                        await conn.commit()

                except Exception as e:
                    print(f"  ⚠️  Error inserting {anime.get('title')}: {e}")
                    continue

            await conn.commit()
            print(f"✓ {len(anime_list)} anime upserted — {embedded} embeddings computed, {skipped} unchanged")

            # Verify
            # Built after the inserts: an index over an empty table is useless to
            # pgvector, and bulk loading into an existing index is slower. Without
            # it every semantic search is a sequential scan of every embedding.
            # --- relations, franchises and the similarity graph -----------------
            # anime.json has carried these since the first fetch and nothing ever
            # loaded them. They are what /api/anime/{id}/related and the Explore
            # graph's franchise collapsing both need.
            print("🔗 Loading relations...")
            await cur.execute("SELECT anilist_id, id FROM anime;")
            by_anilist = dict(await cur.fetchall())

            edges = []
            # Pairs of AniList ids, including ids we did not import. A title
            # outside the 2,500 cannot be a row in related_anime, but it still
            # joins the two titles either side of it: Sound! Euphonium 3 links
            # only to Ensemble Contest, which links to the movie, which links
            # to seasons 1 and 2. Dropping those ids split that franchise in
            # two. Bridging through them merges 24 components and leaves the
            # largest at 28 (Dragon Ball), so it does not run away.
            links = []
            for anime in anime_list:
                src = by_anilist.get(anime["id"])
                for rel in anime.get("relations") or []:
                    if rel.get("to_id") is not None:
                        links.append((anime["id"], rel["to_id"]))
                    dst = by_anilist.get(rel.get("to_id"))
                    if src is not None and dst is not None and dst != src:
                        edges.append((src, dst, rel.get("type") or "RELATED"))

            await cur.execute("TRUNCATE related_anime;")
            if edges:
                await cur.executemany(
                    "INSERT INTO related_anime (anime_id_from, anime_id_to, relationship_type) "
                    "VALUES (%s, %s, %s);",
                    edges,
                )
            print(f"   {len(edges)} relation edges")

            # Franchise = connected component over those edges. Union-find here
            # rather than a recursive CTE: 2,500 nodes is nothing, and this is
            # far easier to read.
            await cur.execute("ALTER TABLE anime ADD COLUMN IF NOT EXISTS franchise_id INTEGER;")
            parent: dict[int, int] = {}

            def find(x: int) -> int:
                parent.setdefault(x, x)
                while parent[x] != x:
                    parent[x] = parent[parent[x]]
                    x = parent[x]
                return x

            for src, dst in links:
                ra, rb = find(src), find(dst)
                if ra != rb:
                    parent[ra] = rb

            # keyed by AniList id above, so group our rows by their component
            groups: dict[int, list[int]] = {}
            for anilist_id, aid in by_anilist.items():
                groups.setdefault(find(anilist_id), []).append(aid)
            assignments = [(min(members), aid) for members in groups.values() for aid in members]
            await cur.executemany("UPDATE anime SET franchise_id = %s WHERE id = %s;", assignments)
            multi = sum(1 for m in groups.values() if len(m) > 1)
            print(f"   {len(groups)} franchises, {multi} with more than one title")

            # Nearest neighbours, precomputed. One query over the HNSW index
            # builds every edge in about a second; the graph endpoint just reads it.
            print("🕸  Building the similarity graph...")
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS anime_neighbours (
                    anime_id INTEGER NOT NULL,
                    neighbour_id INTEGER NOT NULL,
                    similarity REAL NOT NULL,
                    rank SMALLINT NOT NULL,
                    PRIMARY KEY (anime_id, neighbour_id)
                );
            """)
            await cur.execute("TRUNCATE anime_neighbours;")
            await cur.execute("""
                INSERT INTO anime_neighbours (anime_id, neighbour_id, similarity, rank)
                SELECT e1.anime_id, n.anime_id, (1 - n.d)::real,
                       row_number() OVER (PARTITION BY e1.anime_id ORDER BY n.d)
                FROM embeddings e1
                CROSS JOIN LATERAL (
                    SELECT e2.anime_id, e1.plot_embedding <=> e2.plot_embedding AS d
                    FROM embeddings e2
                    WHERE e2.anime_id <> e1.anime_id
                    ORDER BY e1.plot_embedding <=> e2.plot_embedding
                    LIMIT %s
                ) n;
            """, (NEIGHBOURS_PER_ANIME,))
            await cur.execute("SELECT count(*) FROM anime_neighbours;")
            print(f"   {(await cur.fetchone())[0]} similarity edges")
            await conn.commit()

            print("📐 Building the vector index...")
            await cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_embeddings_cosine "
                "ON embeddings USING hnsw (plot_embedding vector_cosine_ops);"
            )
            # the last commit is above this, so without one here the index is
            # rolled back when the connection closes
            await conn.commit()

            await cur.execute("SELECT COUNT(*) FROM anime;")
            anime_count = (await cur.fetchone())[0]
            await cur.execute("SELECT COUNT(*) FROM studios;")
            studios_count = (await cur.fetchone())[0]
            await cur.execute("SELECT COUNT(*) FROM embeddings;")
            embedding_count = (await cur.fetchone())[0]

            print("\n✅ Database state:")
            print(f"   Anime: {anime_count}")
            print(f"   Studios: {studios_count}")
            print(f"   Embeddings: {embedding_count}")
            print("   Characters: 0 (will add in Phase 2)")
            await cur.execute("SELECT count(*) FROM related_anime;")
            print(f"   Related Anime: {(await cur.fetchone())[0]}")

    finally:
        await conn.close()

async def main():
    print("🚀 Starting data ingestion (Phase 1+2 schema)...\n")
    await ingest_anime()
    print("\n✅ Done!")

if __name__ == "__main__":
    asyncio.run(main())
