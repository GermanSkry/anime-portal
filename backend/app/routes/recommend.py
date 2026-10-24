from fastapi import APIRouter, Query
from pydantic import BaseModel
from anthropic import Anthropic
import psycopg
from app.config import settings
import json

router = APIRouter(prefix="/api", tags=["recommendations"])

client = Anthropic(api_key=settings.claude_api_key)

class RecommendRequest(BaseModel):
    preferences: str
    count: int = 5

class RecommendationResponse(BaseModel):
    anime_id: int
    title: str
    reason: str
    rating: float
    genres: list

tools = [
    {
        "name": "search_anime_db",
        "description": "Search anime database by keywords and filters. Returns matching anime with basic info.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for anime title or plot"
                },
                "genres": {
                    "type": "string",
                    "description": "Comma-separated genres to filter by (e.g., 'Action,Drama')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of results to return (default 20)",
                    "default": 20
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_anime_details",
        "description": "Get detailed information about a specific anime by ID",
        "input_schema": {
            "type": "object",
            "properties": {
                "anime_id": {
                    "type": "integer",
                    "description": "The anime ID"
                }
            },
            "required": ["anime_id"]
        }
    }
]

async def search_anime_db(query: str, genres: str = None, limit: int = 20) -> list:
    """Search anime database"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)
    try:
        async with conn.cursor() as cur:
            sql = """
                SELECT a.id, a.title, a.rating, a.genres, a.plot
                FROM anime a
                WHERE a.title ILIKE %s
            """
            params = [f"%{query}%"]

            if genres:
                genre_list = [g.strip() for g in genres.split(",")]
                sql += " AND a.genres && %s"
                params.append(genre_list)

            sql += " ORDER BY a.rating DESC LIMIT %s"
            params.append(limit)

            await cur.execute(sql, params)
            results = await cur.fetchall()

            return [
                {
                    "id": r[0],
                    "title": r[1],
                    "rating": r[2],
                    "genres": r[3] or [],
                    "plot": r[4][:200] if r[4] else ""
                }
                for r in results
            ]
    finally:
        await conn.close()

async def get_anime_details(anime_id: int) -> dict:
    """Get anime details by ID"""
    conn = await psycopg.AsyncConnection.connect(settings.database_url)
    try:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT a.id, a.title, a.rating, a.plot, a.genres, a.year,
                       COALESCE(array_agg(s.name) FILTER (WHERE s.name IS NOT NULL), '{}')
                FROM anime a
                LEFT JOIN anime_studios asas ON a.id = asas.anime_id
                LEFT JOIN studios s ON asas.studio_id = s.id
                WHERE a.id = %s
                GROUP BY a.id
            """, (anime_id,))

            result = await cur.fetchone()
            if not result:
                return {"error": "Anime not found"}

            return {
                "id": result[0],
                "title": result[1],
                "rating": result[2],
                "plot": result[3],
                "genres": result[4] or [],
                "year": result[5],
                "studios": list(result[6]) if result[6] else []
            }
    finally:
        await conn.close()

async def process_tool_call(tool_name: str, tool_input: dict):
    """Execute tool calls from Claude"""
    if tool_name == "search_anime_db":
        return await search_anime_db(
            query=tool_input.get("query"),
            genres=tool_input.get("genres"),
            limit=tool_input.get("limit", 20)
        )
    elif tool_name == "get_anime_details":
        return await get_anime_details(tool_input.get("anime_id"))
    return {"error": "Unknown tool"}

@router.post("/recommend")
async def recommend_anime(request: RecommendRequest):
    """Get AI-powered anime recommendations based on preferences"""

    messages = [
        {
            "role": "user",
            "content": f"""Based on these user preferences: "{request.preferences}"

Please recommend {request.count} anime from our database.
1. Use search_anime_db to find relevant anime matching their preferences
2. Use get_anime_details to get full info on promising candidates
3. Rank and select the top {request.count} matches
4. For each recommendation, provide a 1-sentence reason why it matches their preferences

Format your final answer as JSON array with this structure:
[{{"anime_id": <id>, "title": "<title>", "reason": "<why this matches>", "rating": <rating>, "genres": [...]}}]
"""
        }
    ]

    # Agentic loop
    while True:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            tools=tools,
            messages=messages
        )

        # Check if Claude is done
        if response.stop_reason == "end_turn":
            # Extract JSON from final response
            for block in response.content:
                if hasattr(block, 'text'):
                    text = block.text
                    try:
                        # Find JSON array in response
                        start = text.find('[')
                        end = text.rfind(']') + 1
                        if start != -1 and end > start:
                            json_str = text[start:end]
                            return json.loads(json_str)
                    except:
                        pass
            return {"error": "Could not parse recommendations"}

        # Handle tool calls
        if response.stop_reason == "tool_use":
            # Add assistant message
            messages.append({"role": "assistant", "content": response.content})

            # Process all tool uses
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_result = await process_tool_call(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(tool_result)
                    })

            # Add tool results to messages
            messages.append({"role": "user", "content": tool_results})
        else:
            # Unexpected stop reason
            break

    return {"error": "Recommendation generation failed"}
