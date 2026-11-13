"""Claude agent with smart database-first search + optional web search"""
import re

import psycopg
from openai import OpenAI

from app.config import settings
from app.utils.web_search import search_web

client = OpenAI(
    api_key=settings.openrouter_api_key,
    base_url="https://openrouter.ai/api/v1"
)

# Words that carry no meaning for a catalogue search. Genre words (action, drama,
# romance, mecha...) are deliberately absent: those are exactly what we want to match.
_FILLER = {
    "a", "an", "the", "some", "any", "one", "two", "me", "my", "i", "you", "it",
    "is", "are", "was", "were", "be", "can", "could", "would", "will", "do", "does",
    "and", "or", "but", "for", "with", "about", "like", "that", "this", "these",
    "of", "to", "in", "on", "at", "from", "by", "as",
    "anime", "series", "show", "shows", "movie", "movies", "title", "titles",
    "recommend", "recommendation", "recommendations", "suggest", "suggestion",
    "find", "search", "looking", "look", "want", "give", "tell", "name", "list",
    "good", "great", "best", "nice", "cool", "popular", "please", "something",
    "what", "whats", "which", "who", "how", "where", "when", "why", "short", "long",
    "anything", "anyone", "there", "here", "hello", "hey", "hi", "thanks", "thank",
    "yes", "not", "dont", "cant", "really", "very", "more", "also", "then", "than",
    "them", "they", "your", "their", "have", "has", "had", "get", "got", "make",
}


def extract_terms(query: str) -> list[str]:
    """Pull the searchable words out of a sentence.

    The agent hands us whole messages like "suggest a mecha anime", which match no
    title, plot or genre as a single string. Searching the words separately does.
    """
    words = [w.replace("'", "") for w in re.findall(r"[a-z0-9']+", query.lower())]
    terms = []
    for w in words:
        if len(w) <= 2 or w in _FILLER or w in terms:
            continue
        terms.append(w)
        # "ninjas" must find "ninja"; crude but it covers the plurals people type
        singular = w[:-1]
        if w.endswith("s") and not w.endswith("ss") and len(singular) > 2 and singular not in _FILLER:
            terms.append(singular)
    # nothing but filler: fall back to the raw phrase rather than matching everything
    return terms or ([query.strip()] if query.strip() else [])


async def search_anime_db(query: str, limit: int = 5) -> list[dict]:
    """Search anime database by any meaningful word in the query"""
    terms = extract_terms(query)
    if not terms:
        return []

    conn = await psycopg.AsyncConnection.connect(settings.database_url)
    try:
        async with conn.cursor() as cur:
            # hits = how many of the query's words this anime matches, so "mecha school"
            # ranks a mecha school series above something that only matches one word.
            # Genres are stored capitalised ("Mecha"), so every comparison ignores case.
            await cur.execute("""
                SELECT id, title, rating, year, genres, plot FROM (
                    SELECT a.id, a.title, a.rating, a.year, a.genres, a.plot,
                           (SELECT count(*) FROM unnest(%s::text[]) t
                             WHERE a.title ILIKE '%%' || t || '%%'
                                OR a.plot ILIKE '%%' || t || '%%'
                                OR EXISTS (SELECT 1 FROM unnest(a.genres) g WHERE g ILIKE t)
                           ) AS hits
                    FROM anime a
                ) m
                WHERE hits > 0
                ORDER BY hits DESC, rating DESC NULLS LAST
                LIMIT %s
            """, (terms, limit))

            results = await cur.fetchall()
            return [
                {
                    "id": r[0],
                    "title": r[1],
                    "rating": r[2],
                    "year": r[3],
                    "genres": r[4] or [],
                    "plot": r[5][:150] if r[5] else ""
                }
                for r in results
            ]
    finally:
        await conn.close()

async def chat_with_claude(messages: list[dict]) -> str:
    """Chat with Claude, intelligently using database first, then web search if needed"""
    augmented_messages = messages.copy()
    user_message = messages[-1]["content"].lower() if messages else ""

    # Detect if user is asking for anime search/recommendation
    search_keywords = ["search", "find", "recommend", "suggest", "like", "similar", "what anime", "compare", "good", "action", "drama", "romance", "sci-fi", "horror"]
    needs_search = any(keyword in user_message for keyword in search_keywords)

    # Detect if user wants current/trending info (might need web search)
    web_keywords = ["trending", "current", "recent", "latest", "airing", "news", "review", "upcoming", "popular now", "this season", "popular in", "most popular", "top anime", "2024", "2025", "2026", "future", "will release", "release soon", "coming soon", "next season"]
    needs_web_search = any(keyword in user_message for keyword in web_keywords)

    augmented_content = messages[-1]["content"]
    db_results = []
    web_results = []

    # Extract search term once
    search_term = user_message
    for phrase in ["like ", "similar to ", "for ", "about ", "trending ", "recent ", "by ", "from "]:
        if phrase in search_term:
            search_term = search_term.split(phrase)[-1]
            break

    search_term = search_term.replace("from the database", "").replace("from our database", "").replace("in the database", "").strip()
    search_term = search_term.strip('?.!,;:')

    # STEP 1: Try database search first (saves web quota)
    if (needs_search or needs_web_search) and search_term and len(search_term) > 1:
        db_results = await search_anime_db(search_term, limit=5)

    # STEP 2: Add database results if found
    if db_results:
        results_text = "\n[Database Search Results]\n"
        for anime in db_results:
            results_text += f"• {anime['title']} (★{anime['rating']}/10, {anime['year']}, {', '.join(anime['genres'])})\n"
            results_text += f"  {anime['plot']}\n"

        augmented_content += results_text + "\nUse these database results when answering the user's question."

    # STEP 3: Only search web if:
    # - User explicitly wants current/trending info AND
    # - We either have no DB results OR user explicitly asks for news/reviews
    if needs_web_search and search_term and len(search_term) > 1:  # noqa: SIM102 - kept nested so each condition keeps its comment
        # Only do web search if no good DB results, or if user explicitly wants current info
        if not db_results or any(word in user_message for word in ["news", "review", "trending", "current"]):
            web_results = await search_web(f"{search_term} anime", limit=3)

    # STEP 4: Add web results if found
    if web_results:
        web_text = "\n[Web Search Results - Current Info]\n"
        for result in web_results:
            web_text += f"• {result['title']}\n"
            web_text += f"  {result['snippet']}\n"
            web_text += f"  {result['url']}\n"

        augmented_content += web_text + "\nInclude this current information in your answer."

    # STEP 5: If no DB results and user wants trending info, tell Claude it can suggest web search
    if not db_results and needs_web_search and not web_results:
        augmented_content += "\n[Note: No database results found. You can offer to search the web for current trending information, or share what you know from general knowledge.]"

    # Update message with augmented content
    augmented_messages[-1]["content"] = augmented_content

    # Get response from Claude
    response = client.chat.completions.create(
        model=settings.model_name,
        max_tokens=2048,
        messages=augmented_messages
    )

    return response.choices[0].message.content or "No response"
