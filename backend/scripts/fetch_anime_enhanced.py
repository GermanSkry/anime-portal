#!/usr/bin/env python3
"""Fetch enhanced anime data from AniList API (characters, relations, tags)"""
import asyncio
import json
import os
from pathlib import Path

import httpx

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
      tags {
        name
        rank
        isMediaSpoiler
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

            response = None
            for attempt in range(5):
                response = await client.post(
                    "https://graphql.anilist.co",
                    json={
                        "query": ANILIST_QUERY,
                        "variables": {"page": page, "perPage": 50}
                    },
                    timeout=30.0
                )
                if response.status_code != 429:
                    break
                # AniList runs a degraded 30 requests/minute and answers 429 with
                # the seconds to wait. Skipping the page instead would silently
                # drop 50 titles from the output.
                wait = int(response.headers.get("retry-after", 60))
                print(f"  rate limited, waiting {wait}s (attempt {attempt + 1}/5)")
                await asyncio.sleep(wait + 1)

            if response is None or response.status_code != 200:
                raise RuntimeError(
                    f"page {page} failed with {response.status_code if response else 'no response'}; "
                    "stopping rather than writing a partial file"
                )

            data = response.json()
            if "errors" in data:
                print(f"GraphQL error: {data['errors']}")
                continue

            media_list = data.get("data", {}).get("Page", {}).get("media", [])

            for anime in media_list:
                try:
                    # Parse anime data
                    title = anime.get("title", {}).get("english") or anime.get("title", {}).get("romaji")

                    # AniList removed Media.themes; tags carry the same kind of
                    # descriptor ("Time Manipulation", "Military") and are ranked.
                    # Spoiler tags are dropped — they show up in search results.
                    themes = [
                        t["name"]
                        for t in sorted(
                            (anime.get("tags") or []),
                            key=lambda t: t.get("rank") or 0,
                            reverse=True,
                        )
                        if t.get("name") and not t.get("isMediaSpoiler")
                    ][:8]

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
            # 30 requests/minute is AniList's degraded limit; stay under it
            await asyncio.sleep(float(os.getenv("ANILIST_DELAY", "2.5")))

    return {
        "anime": anime_list,
        "characters": list(characters_map.values()),
        "relations": relations_list
    }

async def main():
    print("🔄 Fetching enhanced anime data from AniList (with characters & relations)...\n")
    # 50 pages x 50 per page. AniList sorts by POPULARITY_DESC, so this is the
    # popular end of the catalogue; going much deeper reaches unrated entries
    # that make search worse rather than better.
    pages = int(os.getenv("ANILIST_PAGES", "50"))
    data = await fetch_anime_data(pages=pages)

    # Save to JSON files
    anime_file = DATA_DIR / "anime.json"
    fetched = len(data["anime"])
    if fetched == 0:
        raise RuntimeError("fetched nothing; leaving the existing file alone")
    if anime_file.exists():
        with open(anime_file) as f:
            existing = len(json.load(f))
        if fetched < existing * 0.9 and os.getenv("ANILIST_FORCE") != "1":
            raise RuntimeError(
                f"fetched {fetched} but {anime_file.name} already holds {existing}. "
                "Refusing to shrink it — set ANILIST_FORCE=1 if that is intended."
            )
    # write via a temp file so a crash mid-write cannot truncate the real one
    tmp = anime_file.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(data["anime"], f, indent=2)
    tmp.replace(anime_file)

    print("\n✅ Data saved:")
    print(f"   Anime: {anime_file} ({len(data['anime'])} entries)")
    print(f"   Characters: {len(data['characters'])} unique characters")
    print(f"   Relations: {len(data['relations'])} anime relationships")
    print("\n📊 Statistics:")
    total_chars = sum(len(a.get("characters", [])) for a in data["anime"])
    print(f"   Total character mentions: {total_chars}")
    print(f"   Avg characters per anime: {total_chars / len(data['anime']):.1f}")
    print(f"   Avg themes per anime: {sum(len(a.get('themes', [])) for a in data['anime']) / len(data['anime']):.1f}")

if __name__ == "__main__":
    asyncio.run(main())
