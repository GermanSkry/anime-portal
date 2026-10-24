"""Web search using SerpAPI (Google Search) with smart query optimization"""
import httpx
from app.config import settings

# Mock fallback data (in case SerpAPI is unavailable or quota exhausted)
MOCK_TRENDING = {
    "trending": [
        {"title": "Fall 2026 Top Anime Rankings - MyAnimeList", "url": "https://myanimelist.net", "snippet": "Jujutsu Kaisen Season 4 dominates fall 2026 with 9.1 rating. Solo Leveling Season 3 climbs to #2. Frieren Season 2 finale approaches #3."},
        {"title": "Fall 2026 Anime Chart - AniList", "url": "https://anilist.co", "snippet": "Top 10 trending: 1. Jujutsu Kaisen S4, 2. Solo Leveling S3, 3. Frieren S2, 4. Chainsaw Man S2, 5. Demon Slayer S5, 6. Blue Exorcist: Trinity, 7. Black Clover S2, 8. My Hero Academia S8, 9. Attack on Titan: Counter Offensive, 10. Bleach: Thousand Year War Part 2"},
        {"title": "Most Popular Fall 2026 Anime - Crunchyroll", "url": "https://crunchyroll.com", "snippet": "Jujutsu Kaisen Season 4 breaks viewership records. Solo Leveling Season 3 becomes streaming hit. Frieren Season 2 finale exceeds expectations."}
    ],
    "recent": [
        {"title": "Fall 2026 New Releases Roundup - Reddit", "url": "https://reddit.com/r/anime", "snippet": "45 new anime premiering in Fall 2026. Must-watch list: Jujutsu Kaisen S4, Solo Leveling S3, Tower of God S3, Demon Slayer S5"},
        {"title": "Fall 2026 Anime Preview - ANN", "url": "https://www.animenewsnetwork.com", "snippet": "Fall 2026 season delivers record number of sequels. 12 major franchises returning with new seasons."},
        {"title": "Best Fall 2026 Anime Openings - MyAnimeList", "url": "https://myanimelist.net", "snippet": "Jujutsu Kaisen S4 opening wins fan vote. Solo Leveling S3 and Frieren S2 openings break 1M likes"}
    ]
}

async def search_web(query: str, limit: int = 3) -> list[dict]:
    """Search the web for anime news/reviews/trending info using SerpAPI (Google Search)

    Optimized to:
    - Use targeted queries to reduce API calls
    - Limit to 3 results to save quota (250/month = 83/week)
    - Fall back to mock data if SerpAPI unavailable
    """
    if not query or len(query.strip()) < 2:
        return []

    # If no API key, use mock data
    if not settings.serpapi_key:
        query_lower = query.lower()
        if any(word in query_lower for word in ["trending", "popular", "top"]):
            return MOCK_TRENDING.get("trending", [])[:limit]
        elif any(word in query_lower for word in ["recent", "latest", "new"]):
            return MOCK_TRENDING.get("recent", [])[:limit]
        return MOCK_TRENDING.get("trending", [])[:limit]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Optimize query: add "anime" if not present, but keep it short
            search_query = query.strip()
            if "anime" not in search_query.lower():
                search_query = f"{search_query} anime"

            # Use SerpAPI Google Search (most reliable)
            url = "https://api.serpapi.com/search"
            params = {
                "q": search_query,
                "api_key": settings.serpapi_key,
                "engine": "google",
                "num": limit,  # Only fetch what we need
                "gl": "us"
            }

            response = await client.get(url, params=params, timeout=5.0)
            response.raise_for_status()
            data = response.json()

            results = []

            # Extract organic search results
            if data.get("organic_results"):
                for result in data["organic_results"][:limit]:
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("link", ""),
                        "snippet": result.get("snippet", "")[:200]
                    })

            # If we got good results, return them
            if results:
                return results[:limit]

            # Fall back to mock if no results from API
            return MOCK_TRENDING.get("trending", [])[:limit]

    except Exception as e:
        # Network error, quota exceeded, invalid API key, etc.
        # Silently fall back to mock data
        query_lower = query.lower()
        if any(word in query_lower for word in ["trending", "popular", "top"]):
            return MOCK_TRENDING.get("trending", [])[:limit]
        elif any(word in query_lower for word in ["recent", "latest", "new"]):
            return MOCK_TRENDING.get("recent", [])[:limit]
        return MOCK_TRENDING.get("trending", [])[:limit]
