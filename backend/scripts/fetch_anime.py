#!/usr/bin/env python3
"""Fetch anime data from AniList API"""
import httpx
import json
import asyncio
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

ANILIST_QUERY = """
query ($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    media(sort: POPULARITY_DESC, type: ANIME) {
      id
      title {
        english
        romaji
      }
      startDate {
        year
      }
      averageScore
      description
      coverImage {
        large
      }
      genres
      studios(isMain: true) {
        nodes {
          name
        }
      }
    }
  }
}
"""

async def fetch_anime_data(pages: int = 5) -> list:
    """Fetch top anime from AniList API"""
    all_anime = []

    async with httpx.AsyncClient() as client:
        for page in range(1, pages + 1):
            print(f"Fetching page {page}...")

            response = await client.post(
                "https://graphql.anilist.co",
                json={
                    "query": ANILIST_QUERY,
                    "variables": {"page": page, "perPage": 50}
                }
            )

            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                continue

            data = response.json()
            media_list = data.get("data", {}).get("Page", {}).get("media", [])

            for anime in media_list:
                try:
                    # Parse anime data
                    processed = {
                        "id": anime.get("id"),
                        "title": anime.get("title", {}).get("english") or anime.get("title", {}).get("romaji"),
                        "title_english": anime.get("title", {}).get("english"),
                        "year": anime.get("startDate", {}).get("year"),
                        "rating": (anime.get("averageScore") or 0) / 10,  # Convert to 0-10 scale
                        "plot": anime.get("description", "").replace("<br>", " ")[:500],  # Truncate
                        "cover_image": anime.get("coverImage", {}).get("large"),
                        "genres": anime.get("genres", []),
                        "studios": [s["name"] for s in anime.get("studios", {}).get("nodes", [])]
                    }
                    all_anime.append(processed)
                except Exception as e:
                    print(f"Error processing anime: {e}")
                    continue

            print(f"  Fetched {len(media_list)} anime")
            await asyncio.sleep(1)  # Rate limiting

    return all_anime

async def main():
    print("🔄 Fetching anime data from AniList...")
    anime_list = await fetch_anime_data(pages=5)  # 250 anime

    # Save to JSON
    output_file = DATA_DIR / "anime.json"
    with open(output_file, "w") as f:
        json.dump(anime_list, f, indent=2)

    print(f"✓ Saved {len(anime_list)} anime to {output_file}")
    print(f"  File size: {output_file.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    asyncio.run(main())
