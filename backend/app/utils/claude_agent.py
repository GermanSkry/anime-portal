"""Claude agent with anime DB search augmentation"""
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
    """Chat with Claude, augmenting with anime DB and web search for relevant queries"""
    augmented_messages = messages.copy()
    user_message = messages[-1]["content"].lower() if messages else ""

    # Detect if user is asking for anime search/recommendation
    search_keywords = ["search", "find", "recommend", "suggest", "like", "similar", "what anime", "compare", "good"]
    needs_search = any(keyword in user_message for keyword in search_keywords)

    # Detect if user wants current/trending info (needs web search)
    web_keywords = ["trending", "current", "recent", "latest", "airing", "news", "review", "upcoming", "popular now", "this season", "popular in", "most popular", "top anime", "2024", "2025", "2026"]
    needs_web_search = any(keyword in user_message for keyword in web_keywords)

    augmented_content = messages[-1]["content"]

    if needs_search or needs_web_search:
        # Extract potential search term
        search_term = user_message
        for phrase in ["like ", "similar to ", "for ", "about ", "trending ", "recent ", "about "]:
            if phrase in search_term:
                search_term = search_term.split(phrase)[-1]
                break

        search_term = search_term.replace("from the database", "").replace("from our database", "").replace("in the database", "").strip()
        search_term = search_term.strip('?.!,;:')

        # Search database if we have a reasonable search term
        db_results = []
        if needs_search and search_term and len(search_term) > 1:
            db_results = await search_anime_db(search_term, limit=3)

        if db_results:
            results_text = "\n[Database Search Results]\n"
            for anime in db_results:
                results_text += f"• {anime['title']} (★{anime['rating']}/10, {anime['year']}, {', '.join(anime['genres'])})\n"
                results_text += f"  {anime['plot']}\n"

            augmented_content += results_text + "\nUse these database results when answering the user's question."

        # Web search for trending/current info
        if needs_web_search and search_term and len(search_term) > 1:
            web_results = await search_web(f"{search_term} anime", limit=3)

            if web_results:
                web_text = "\n[Web Search Results - Current Info]\n"
                for result in web_results:
                    web_text += f"• {result['title']}\n"
                    web_text += f"  {result['snippet']}\n"
                    web_text += f"  {result['url']}\n"

                augmented_content += web_text + "\nInclude this current information in your answer."

    # Update message with augmented content
    augmented_messages[-1]["content"] = augmented_content

    # Get response from Claude
    response = client.chat.completions.create(
        model=settings.model_name,
        max_tokens=2048,
        messages=augmented_messages
    )

    return response.choices[0].message.content or "No response"
