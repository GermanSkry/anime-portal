#!/usr/bin/env python3
"""Fetch anime data from AniList API with trailers (Phase 1.5)"""
import httpx
import json
import asyncio
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# AniList query with trailers, descriptions
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
      trailer {
        id
        site
        thumbnail
      }
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
    """Fetch anime from AniList API with trailers"""
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

                        # Build trailer URL
                        trailer_url = None
                        if anime.get("trailer"):
                            trailer = anime.get("trailer", {})
                            if trailer.get("site") == "youtube" and trailer.get("id"):
                                trailer_url = f"https://www.youtube.com/watch?v={trailer.get('id')}"

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
                            "trailer_url": trailer_url,
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
    print("🔄 Fetching anime data with trailers (Phase 1.5)...\n")
    anime_list = await fetch_anime_data(pages=5)

    if not anime_list:
        print("\n⚠️  No data fetched. Using sample data for testing...\n")
        anime_list = create_sample_data()

    # Save to JSON
    output_file = DATA_DIR / "anime.json"
    with open(output_file, "w") as f:
        json.dump(anime_list, f, indent=2)

    print(f"\n✅ Data saved:")
    print(f"   Anime: {output_file}")
    print(f"   Total: {len(anime_list)} entries")

    # Count trailers
    trailers = sum(1 for a in anime_list if a.get("trailer_url"))
    print(f"   Trailers: {trailers}/{len(anime_list)} ({100*trailers/len(anime_list):.0f}%)")

    print(f"\n📊 Sample anime with trailer:")
    for anime in anime_list:
        if anime.get("trailer_url"):
            print(f"   - {anime['title']} | {anime['trailer_url']}")
            break

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
            "trailer_url": "https://www.youtube.com/watch?v=NzUHNEZN20E",
            "genres": ["Action", "Drama", "Fantasy"],
            "themes": ["War", "Survival"],
            "studios": ["Wit Studio"],
            "characters": [],
            "relations": []
        },
    ]

if __name__ == "__main__":
    asyncio.run(main())
