#!/usr/bin/env python3
"""Fetch enhanced anime data from AniList API (characters, relations, themes)"""
import httpx
import json
import asyncio
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# AniList GraphQL query (includes characters, relations, themes)
ANILIST_QUERY = """
query ($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
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
      themes {
        edges {
          node {
            name
          }
        }
      }
      studios(isMain: true) {
        nodes {
          name
        }
      }
      characters(sort: ROLE, perPage: 5) {
        edges {
          node {
            id
            name {
              full
              native
            }
            image {
              large
            }
          }
          role
        }
      }
      relations {
        edges {
          node {
            id
            title {
              english
              romaji
            }
          }
          relationType
        }
      }
    }
  }
}
"""

async def fetch_anime_data(pages: int = 5) -> dict:
    """Fetch enhanced anime data from AniList API"""
    anime_list = []
    characters_map = {}  # For deduplication
    relations_list = []

    async with httpx.AsyncClient() as client:
        for page in range(1, pages + 1):
            print(f"Fetching page {page}...")

            response = await client.post(
                "https://graphql.anilist.co",
                json={
                    "query": ANILIST_QUERY,
                    "variables": {"page": page, "perPage": 50}
                },
                timeout=30.0
            )

            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                continue

            data = response.json()
            if "errors" in data:
                print(f"GraphQL error: {data['errors']}")
                continue

            media_list = data.get("data", {}).get("Page", {}).get("media", [])

            for anime in media_list:
                try:
                    # Parse anime data
                    title = anime.get("title", {}).get("english") or anime.get("title", {}).get("romaji")

                    # Extract themes
                    themes = []
                    for theme_edge in anime.get("themes", {}).get("edges", []):
                        theme_name = theme_edge.get("node", {}).get("name")
                        if theme_name:
                            themes.append(theme_name)

                    # Extract characters
                    characters = []
                    for char_edge in anime.get("characters", {}).get("edges", []):
                        char_node = char_edge.get("node", {})
                        char_id = char_node.get("id")
                        char_name = char_node.get("name", {}).get("full")
                        char_role = char_edge.get("role", "SUPPORTING")
                        char_image = char_node.get("image", {}).get("large")

                        if char_name:
                            characters.append({
                                "id": char_id,
                                "name": char_name,
                                "role": char_role,
                                "image": char_image
                            })

                            # Add to dedup map
                            if char_id not in characters_map:
                                characters_map[char_id] = {
                                    "id": char_id,
                                    "name": char_name,
                                    "image": char_image
                                }

                    # Extract relations (sequels, prequels, etc)
                    relations = []
                    for rel_edge in anime.get("relations", {}).get("edges", []):
                        rel_node = rel_edge.get("node", {})
                        related_id = rel_node.get("id")
                        relation_type = rel_edge.get("relationType", "OTHER")

                        if related_id and relation_type in ["SEQUEL", "PREQUEL", "SPIN_OFF", "SIDE_STORY"]:
                            relations.append({
                                "from_id": anime.get("id"),
                                "to_id": related_id,
                                "type": relation_type,
                                "title": rel_node.get("title", {}).get("english") or rel_node.get("title", {}).get("romaji")
                            })

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
                        "plot": anime.get("description", "").replace("<br>", " ")[:500],
                        "cover_image": anime.get("coverImage", {}).get("large"),
                        "banner_image": anime.get("bannerImage"),
                        "genres": anime.get("genres", []),
                        "themes": themes,
                        "studios": [s["name"] for s in anime.get("studios", {}).get("nodes", [])],
                        "characters": characters,
                        "relations": relations
                    }
                    anime_list.append(processed)
                    relations_list.extend(relations)

                except Exception as e:
                    print(f"Error processing anime: {e}")
                    continue

            print(f"  Fetched {len(media_list)} anime")
            await asyncio.sleep(1)  # Rate limiting

    return {
        "anime": anime_list,
        "characters": list(characters_map.values()),
        "relations": relations_list
    }

async def main():
    print("🔄 Fetching enhanced anime data from AniList (with characters & relations)...\n")
    data = await fetch_anime_data(pages=5)  # 250 anime

    # Save to JSON files
    anime_file = DATA_DIR / "anime.json"
    with open(anime_file, "w") as f:
        json.dump(data["anime"], f, indent=2)

    print(f"\n✅ Data saved:")
    print(f"   Anime: {anime_file} ({len(data['anime'])} entries)")
    print(f"   Characters: {len(data['characters'])} unique characters")
    print(f"   Relations: {len(data['relations'])} anime relationships")
    print(f"\n📊 Statistics:")
    total_chars = sum(len(a.get("characters", [])) for a in data["anime"])
    print(f"   Total character mentions: {total_chars}")
    print(f"   Avg characters per anime: {total_chars / len(data['anime']):.1f}")
    print(f"   Avg themes per anime: {sum(len(a.get('themes', [])) for a in data['anime']) / len(data['anime']):.1f}")

if __name__ == "__main__":
    asyncio.run(main())
