#!/usr/bin/env python3
"""Update anime trailers from anime.json"""
import json
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from app.config import settings

DATA_DIR = Path(__file__).parent.parent / "data"
ANIME_FILE = DATA_DIR / "anime.json"

async def update_trailers():
    if not ANIME_FILE.exists():
        print(f"❌ Data file not found: {ANIME_FILE}")
        return

    print(f"📥 Loading anime from {ANIME_FILE}...")
    with open(ANIME_FILE) as f:
        anime_list = json.load(f)

    print(f"   Loaded {len(anime_list)} anime")

    conn = await psycopg.AsyncConnection.connect(settings.database_url)

    try:
        async with conn.cursor() as cur:
            # Update trailers for existing anime
            updated = 0
            for i, anime in enumerate(anime_list):
                try:
                    await cur.execute(
                        """
                        UPDATE anime
                        SET trailer_url = %s
                        WHERE anilist_id = %s;
                        """,
                        (anime.get("trailer_url"), anime["id"])
                    )
                    if anime.get("trailer_url"):
                        updated += 1

                    if (i + 1) % 50 == 0:
                        await conn.commit()
                        print(f"  Processed {i + 1}/{len(anime_list)}")
                except Exception as e:
                    print(f"  ⚠️  Error updating {anime.get('title')}: {e}")
                    continue

            await conn.commit()
            print(f"✓ Updated {updated} anime with trailer URLs")

            # Verify
            await cur.execute("SELECT COUNT(*) FROM anime WHERE trailer_url IS NOT NULL AND trailer_url != '';")
            with_trailer = (await cur.fetchone())[0]
            print(f"\n✅ Anime with trailers: {with_trailer}")

    finally:
        await conn.close()

async def main():
    print("🚀 Updating anime trailers...\n")
    await update_trailers()
    print("\n✅ Done!")

if __name__ == "__main__":
    asyncio.run(main())
