#!/usr/bin/env python3
"""Fetch anime data from AniList API (simplified, more reliable)"""
import httpx
import json
import asyncio
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Simpler, more reliable AniList query
ANILIST_QUERY = """
query ($page: Int) {
  Page(page: $page, perPage: 50) {
    media(sort: POPULARITY_DESC, type: ANIME) {
      id
      title {
        english
        romaji
        native
      }
      startDate {
        year
      }
      season
      episodes
      status
      averageScore
      description
      coverImage {
        large
      }
      bannerImage
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
    """Fetch anime from AniList API"""
    anime_list = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for page in range(1, pages + 1):
            print(f"Fetching page {page}...")

            try:
                response = await client.post(
                    "https://graphql.anilist.co",
                    json={
                        "query": ANILIST_QUERY,
                        "variables": {"page": page}
                    }
                )

                if response.status_code != 200:
                    print(f"  ⚠️  Status {response.status_code}, skipping...")
                    continue

                data = response.json()

                if "errors" in data:
                    print(f"  ⚠️  GraphQL error: {data['errors'][0].get('message', 'Unknown')}")
                    continue

                media_list = data.get("data", {}).get("Page", {}).get("media", [])

                if not media_list:
                    print(f"  No data returned")
                    continue

                for anime in media_list:
                    try:
                        title = anime.get("title", {}).get("english") or anime.get("title", {}).get("romaji")

                        processed = {
                            "id": anime.get("id"),
                            "title": title,
                            "title_english": anime.get("title", {}).get("english"),
                            "title_japanese": anime.get("title", {}).get("native"),
                            "year": anime.get("startDate", {}).get("year"),
                            "season": anime.get("season"),
                            "episodes": anime.get("episodes"),
                            "status": anime.get("status"),
                            "rating": (anime.get("averageScore") or 0) / 10,
                            "plot": anime.get("description", "").replace("<br>", " ")[:500] if anime.get("description") else "",
                            "cover_image": anime.get("coverImage", {}).get("large"),
                            "banner_image": anime.get("bannerImage"),
                            "genres": anime.get("genres", []),
                            "themes": [],
                            "studios": [s["name"] for s in anime.get("studios", {}).get("nodes", [])],
                            "characters": [],
                            "relations": []
                        }
                        anime_list.append(processed)
                    except Exception as e:
                        print(f"    Error processing anime: {e}")
                        continue

                print(f"  ✓ Fetched {len(media_list)} anime")

            except Exception as e:
                print(f"  ❌ Request failed: {e}")
                continue

            await asyncio.sleep(1)  # Rate limiting

    return anime_list

async def main():
    print("🔄 Fetching anime data from AniList...\n")
    anime_list = await fetch_anime_data(pages=5)

    if not anime_list:
        print("\n⚠️  No data fetched. Using sample data for testing...\n")
        # Create minimal test data so Phase 1 can proceed
        anime_list = create_sample_data()

    # Save to JSON
    output_file = DATA_DIR / "anime.json"
    with open(output_file, "w") as f:
        json.dump(anime_list, f, indent=2)

    print(f"\n✅ Data saved:")
    print(f"   Anime: {output_file}")
    print(f"   Total: {len(anime_list)} entries")
    print(f"\n📊 Sample anime:")
    for anime in anime_list[:3]:
        print(f"   - {anime['title']} ({anime['year']}) | Rating: {anime['rating']:.1f} ⭐")

def create_sample_data() -> list:
    """Create minimal sample data for testing if API fails"""
    return [
        {
            "id": 16498,
            "title": "Attack on Titan",
            "title_english": "Attack on Titan",
            "title_japanese": "進撃の巨人",
            "year": 2013,
            "season": "SPRING",
            "episodes": 25,
            "status": "FINISHED",
            "rating": 8.8,
            "plot": "In a world plagued by creatures known as Titans, civilization retreats behind massive walls.",
            "cover_image": "https://s4.anilist.co/file/anilistcdn/media/anime/cover/medium/bx16498-kW0x9XY2NXdd.jpg",
            "banner_image": "https://s4.anilist.co/file/anilistcdn/media/anime/banner/16498.jpg",
            "genres": ["Action", "Drama", "Fantasy"],
            "themes": ["War", "Survival"],
            "studios": ["Wit Studio"],
            "characters": [],
            "relations": []
        },
        {
            "id": 9253,
            "title": "Steins;Gate",
            "title_english": "Steins;Gate",
            "title_japanese": "シュタインズゲート",
            "year": 2011,
            "season": "SPRING",
            "episodes": 24,
            "status": "FINISHED",
            "rating": 9.0,
            "plot": "Okabe, a self-labeled mad scientist, discovers that a microwave can send text messages to the past.",
            "cover_image": "https://s4.anilist.co/file/anilistcdn/media/anime/cover/medium/bx9253-EZvKpPKgWqvh.jpg",
            "banner_image": "https://s4.anilist.co/file/anilistcdn/media/anime/banner/9253.jpg",
            "genres": ["Sci-Fi", "Thriller"],
            "themes": ["Time Travel"],
            "studios": ["White Fox"],
            "characters": [],
            "relations": []
        },
        {
            "id": 21,
            "title": "Fullmetal Alchemist",
            "title_english": "Fullmetal Alchemist",
            "title_japanese": "鋼の錬金術師",
            "year": 2005,
            "season": "FALL",
            "episodes": 51,
            "status": "FINISHED",
            "rating": 8.1,
            "plot": "Two brothers use alchemy to bring their mother back from the dead, but the ritual goes wrong.",
            "cover_image": "https://s4.anilist.co/file/anilistcdn/media/anime/cover/medium/bx21-uYt7K4BtHLlh.jpg",
            "banner_image": "https://s4.anilist.co/file/anilistcdn/media/anime/banner/21.jpg",
            "genres": ["Action", "Adventure", "Drama"],
            "themes": ["Magic"],
            "studios": ["Bones"],
            "characters": [],
            "relations": []
        }
    ]

if __name__ == "__main__":
    asyncio.run(main())
