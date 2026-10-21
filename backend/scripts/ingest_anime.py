#!/usr/bin/env python3
"""Ingest anime data into PostgreSQL with enhanced schema (Phase 1+2)"""
import json
import asyncio
from pathlib import Path
import sys
import os

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from app.config import settings

DATA_DIR = Path(__file__).parent.parent / "data"
ANIME_FILE = DATA_DIR / "anime.json"

async def generate_simple_embedding(text: str) -> list:
    """Generate a simple embedding from text (placeholder)
    In production, use: sentence-transformers, Claude embeddings, or OpenAI
    For now, return a dummy 384-dim vector based on text hash
    """
    import hashlib

    if not text:
        return [0.0] * 384

    # Simple deterministic hashing to 384 dimensions
    hash_obj = hashlib.md5(text.encode())
    seed = int(hash_obj.hexdigest(), 16)

    # Generate pseudo-random values based on seed
    import random
    random.seed(seed)
    embedding = [random.gauss(0, 1) for _ in range(384)]

    # Normalize
    magnitude = sum(x**2 for x in embedding) ** 0.5
    embedding = [x / magnitude for x in embedding]

    return embedding

async def ingest_anime():
    """Load anime data into database with enhanced schema"""
    if not ANIME_FILE.exists():
        print(f"❌ Data file not found: {ANIME_FILE}")
        print("   Run: python scripts/fetch_anime.py")
        return

    print(f"📥 Loading anime from {ANIME_FILE}...")
    with open(ANIME_FILE) as f:
        anime_list = json.load(f)

    print(f"   Loaded {len(anime_list)} anime")

    # Connect to database
    conn = await psycopg.AsyncConnection.connect(settings.database_url)

    try:
        async with conn.cursor() as cur:
            # Initialize DB schema
            print("🔧 Initializing database schema...")
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

            # Embeddings for semantic search
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

            # Create indexes
            print("📑 Creating indexes...")
            await cur.execute("CREATE INDEX IF NOT EXISTS idx_anime_year ON anime(year);")
            await cur.execute("CREATE INDEX IF NOT EXISTS idx_anime_season ON anime(season);")
            await cur.execute("CREATE INDEX IF NOT EXISTS idx_anime_rating ON anime(rating DESC);")
            await cur.execute("CREATE INDEX IF NOT EXISTS idx_anime_genres ON anime USING GIN(genres);")
            await cur.execute("CREATE INDEX IF NOT EXISTS idx_related_from ON related_anime(anime_id_from);")
            await cur.execute("CREATE INDEX IF NOT EXISTS idx_recommendations ON recommendations(anime_id, score DESC);")

            # Clear existing data (for re-ingestion)
            print("🗑️  Clearing old data...")
            await cur.execute("DELETE FROM recommendations;")
            await cur.execute("DELETE FROM anime_characters;")
            await cur.execute("DELETE FROM characters;")
            await cur.execute("DELETE FROM related_anime;")
            await cur.execute("DELETE FROM embeddings;")
            await cur.execute("DELETE FROM anime_studios;")
            await cur.execute("DELETE FROM anime;")
            await cur.execute("DELETE FROM studios;")
            await conn.commit()

            # Insert anime
            print("📝 Inserting anime...")
            for i, anime in enumerate(anime_list):
                try:
                    await cur.execute("""
                        INSERT INTO anime (
                            anilist_id, title, title_english, title_japanese,
                            year, season, episodes, status, rating, plot,
                            cover_image, banner_image, trailer_url, genres, themes
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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

                    # Generate and store embedding
                    plot_text = anime.get("plot", "") or anime.get("title", "")
                    embedding = await generate_simple_embedding(plot_text)
                    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

                    await cur.execute("""
                        INSERT INTO embeddings (anime_id, plot_embedding)
                        VALUES (%s, %s);
                    """, (anime_db_id, embedding_str))

                    if (i + 1) % 50 == 0:
                        print(f"  Processed {i + 1}/{len(anime_list)}")
                        await conn.commit()

                except Exception as e:
                    print(f"  ⚠️  Error inserting {anime.get('title')}: {e}")
                    continue

            await conn.commit()
            print(f"✓ Inserted {len(anime_list)} anime with enhanced schema")

            # Verify
            await cur.execute("SELECT COUNT(*) FROM anime;")
            anime_count = (await cur.fetchone())[0]
            await cur.execute("SELECT COUNT(*) FROM studios;")
            studios_count = (await cur.fetchone())[0]
            await cur.execute("SELECT COUNT(*) FROM embeddings;")
            embedding_count = (await cur.fetchone())[0]

            print(f"\n✅ Database state:")
            print(f"   Anime: {anime_count}")
            print(f"   Studios: {studios_count}")
            print(f"   Embeddings: {embedding_count}")
            print(f"   Characters: 0 (will add in Phase 2)")
            print(f"   Related Anime: 0 (will add in Phase 2)")

    finally:
        await conn.close()

async def main():
    print("🚀 Starting data ingestion (Phase 1+2 schema)...\n")
    await ingest_anime()
    print("\n✅ Done!")

if __name__ == "__main__":
    asyncio.run(main())
