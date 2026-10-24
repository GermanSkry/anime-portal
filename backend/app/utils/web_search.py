"""Web search integration using DuckDuckGo (free, no API key needed)"""
import httpx
import re
from typing import Optional

async def search_web(query: str, limit: int = 5) -> list[dict]:
    """Search the web for anime news/reviews/trending info"""
    if not query or len(query.strip()) < 2:
        return []

    try:
        # DuckDuckGo HTML search (simple scraping)
        async with httpx.AsyncClient(timeout=5.0) as client:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            url = "https://html.duckduckgo.com/"
            params = {"q": query, "t": "h_", "ia": "web"}

            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()

            html = response.text

            # Extract result links and snippets (simple regex parsing)
            results = []

            # Pattern: data-result="...">...<a href="...">...</a>
            pattern = r'<a rel="noopener" class="result__a" href="([^"]+)">([^<]+)</a>.*?<a class="result__snippet"[^>]*>([^<]*(?:<[^>]+>[^<]*)*)</a>'

            matches = re.finditer(pattern, html, re.DOTALL)
            for match in matches:
                if len(results) >= limit:
                    break
                try:
                    url_str = match.group(1)
                    title = match.group(2).strip()
                    snippet = match.group(3).strip()
                    snippet = re.sub(r'<[^>]+>', '', snippet)  # Remove HTML tags

                    if title and url_str:
                        results.append({
                            "title": title,
                            "url": url_str,
                            "snippet": snippet[:200]
                        })
                except (IndexError, AttributeError):
                    continue

            return results[:limit]

    except Exception as e:
        # Fallback: return empty on error
        return []
