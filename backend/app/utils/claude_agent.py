"""Claude agent with smart database-first search + optional web search"""
from openai import OpenAI
from app.config import settings
import psycopg
from app.utils.web_search import search_web

client = OpenAI(
    api_key=settings.openrouter_api_key,
    base_url="https://openrouter.ai/api/v1"
)

async def search_anime_db(query: str, limit: int = 5) -> list[dict]:
    """Search anime database"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)
    try:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT a.id, a.title, a.rating, a.year, a.genres, a.plot
                FROM anime a
                WHERE a.title ILIKE %s OR a.plot ILIKE %s OR a.genres && %s
                ORDER BY a.rating DESC
                LIMIT %s
            """, (f"%{query}%", f"%{query}%", [query], limit))

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
    """Chat with Claude, intelligently using database first, then web search if needed

    Priority order:
    1. Search database for specific anime (saves web quota)
    2. If no DB results and user wants current info → search web
    3. If no results from either → Claude uses general knowledge + suggests web search
    """
    augmented_messages = messages.copy()
    user_message = messages[-1]["content"].lower() if messages else ""

    # Detect if user is asking for anime search/recommendation
    search_keywords = ["search", "find", "recommend", "suggest", "like", "similar", "what anime", "compare", "good"]
    needs_search = any(keyword in user_message for keyword in search_keywords)

    # Detect if user wants current/trending info (might need web search)
    web_keywords = ["trending", "current", "recent", "latest", "airing", "news", "review", "upcoming", "popular now", "this season", "popular in", "most popular", "top anime", "2024", "2025", "2026"]
    needs_web_search = any(keyword in user_message for keyword in web_keywords)

    augmented_content = messages[-1]["content"]
    db_results = []
    web_results = []

    # Extract search term once
    search_term = user_message
    for phrase in ["like ", "similar to ", "for ", "about ", "trending ", "recent "]:
        if phrase in search_term:
            search_term = search_term.split(phrase)[-1]
            break

    search_term = search_term.replace("from the database", "").replace("from our database", "").replace("in the database", "").strip()
    search_term = search_term.strip('?.!,;:')

    # STEP 1: Try database search first (saves web quota)
    if (needs_search or needs_web_search) and search_term and len(search_term) > 1:
        db_results = await search_anime_db(search_term, limit=3)

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
    if needs_web_search and search_term and len(search_term) > 1:
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
