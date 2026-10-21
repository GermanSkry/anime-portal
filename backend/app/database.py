import psycopg
from psycopg import AsyncConnection
from app.config import settings

async def get_db_connection() -> AsyncConnection:
    """Get async database connection"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)
    return conn

async def init_db():
    """Initialize database schema"""
    conn = await get_db_connection()
    async with conn.cursor() as cur:
        # Enable pgvector extension
        await cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # Create anime table
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS anime (
                id SERIAL PRIMARY KEY,
                anilist_id INTEGER UNIQUE NOT NULL,
                title VARCHAR(255) NOT NULL,
                title_english VARCHAR(255),
                year INTEGER,
                rating FLOAT,
                plot TEXT,
                cover_image VARCHAR(255),
                genres TEXT[] DEFAULT '{}',
                studios TEXT[] DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Create embeddings table (for semantic search)
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id SERIAL PRIMARY KEY,
                anime_id INTEGER UNIQUE NOT NULL REFERENCES anime(id) ON DELETE CASCADE,
                plot_embedding vector(384),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Create indices
        await cur.execute("CREATE INDEX IF NOT EXISTS idx_anime_title ON anime(title);")
        await cur.execute("CREATE INDEX IF NOT EXISTS idx_anime_year ON anime(year);")
        await cur.execute("CREATE INDEX IF NOT EXISTS idx_anime_rating ON anime(rating);")

        await conn.commit()
        await conn.close()
        print("✓ Database initialized")

async def query_anime(limit: int = 10, offset: int = 0):
    """Fetch anime list"""
    conn = await get_db_connection()
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT id, anilist_id, title, year, rating, genres, studios, cover_image FROM anime ORDER BY rating DESC LIMIT %s OFFSET %s;",
            (limit, offset)
        )
        results = await cur.fetchall()
    await conn.close()
    return results
