"""LangGraph-based agentic chat system for anime recommendations"""

import re
from typing import TypedDict

from langgraph.graph import END, StateGraph


# ============= STATE DEFINITION =============
class AgentState(TypedDict):
    """Agent state that persists through execution"""
    messages: list[dict]  # Conversation history
    tool_calls: list[dict]  # Tools to execute
    tool_results: list[dict]  # Results from tool execution
    final_response: str  # Final response to user
    anime_references: list[dict]  # Anime titles found in response

# ============= TOOL IMPLEMENTATIONS =============
async def search_anime_db(query: str, limit: int = 5) -> str:
    """Execute database search"""
    from app.utils.claude_agent import search_anime_db as db_search
    results = await db_search(query, limit)

    if not results:
        return f"No anime found matching '{query}'"

    formatted = "Database Results:\n"
    for anime in results:
        formatted += f"- **{anime['title']}** (★{anime['rating']}/10, {anime['year']}, {', '.join(anime['genres'])})\n"
        formatted += f"  {anime['plot']}\n"

    return formatted

async def search_web(query: str) -> str:
    """Execute web search"""
    from app.utils.web_search import search_web as web_search
    results = await web_search(query)

    if not results:
        return f"No web results found for '{query}'"

    formatted = "Web Results (Current Info):\n"
    for result in results[:3]:
        formatted += f"- {result.get('title', 'No title')}\n"
        formatted += f"  {result.get('snippet', '')}\n"

    return formatted

# ============= DECIDE WHICH TOOL =============
async def decide_tool(latest_message: str) -> str:
    """Decide which tool to use based on message"""
    msg_lower = latest_message.lower()

    # Keywords for database search
    db_keywords = ["recommend", "suggest", "action", "drama", "romance", "genre",
                   "anime", "find", "search", "what's", "good", "best", "popular"]

    # Keywords for web search
    web_keywords = ["trending", "current", "latest", "news", "2024", "2025",
                    "upcoming", "airing", "recent", "this season", "popular now"]

    # Check web keywords first (more specific)
    if any(keyword in msg_lower for keyword in web_keywords):
        return "search_web"

    # Check db keywords
    if any(keyword in msg_lower for keyword in db_keywords):
        return "search_db"

    return "none"

# ============= NODES =============
async def decide_node(state: AgentState) -> AgentState:
    """Decide whether to use tools"""
    latest_message = state["messages"][-1]["content"] if state["messages"] else ""
    tool = await decide_tool(latest_message)

    if tool == "search_db":
        state["tool_calls"] = [{
            "id": "search_1",
            "tool": "search_anime_db",
            "query": latest_message
        }]
    elif tool == "search_web":
        state["tool_calls"] = [{
            "id": "search_1",
            "tool": "search_web",
            "query": latest_message
        }]
    else:
        state["tool_calls"] = []

    return state

async def execute_tools_node(state: AgentState) -> AgentState:
    """Execute tool calls"""
    results = []

    for tool_call in state["tool_calls"]:
        tool = tool_call["tool"]
        query = tool_call.get("query", "")

        if tool == "search_anime_db":
            result = await search_anime_db(query)
        elif tool == "search_web":
            result = await search_web(query)
        else:
            result = ""

        results.append({
            "tool": tool,
            "result": result
        })

    state["tool_results"] = results
    return state

async def respond_node(state: AgentState) -> AgentState:
    """Generate response using Claude"""
    from app.utils.claude_agent import chat_with_claude

    # Build context
    context = ""
    if state["tool_results"]:
        context = "\n[Tool Results]\n"
        for result in state["tool_results"]:
            context += result["result"] + "\n"

    # Build messages for Claude
    messages = [
        {
            "role": "system",
            "content": """You are a concise anime recommendation assistant. Keep responses SHORT (2-3 sentences max).

When recommending:
- Format titles as **Title** for clickable links
- List 3-5 titles max
- Include 1-line descriptions
- Be conversational"""
        }
    ]

    # Add conversation history
    for msg in state["messages"]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add context if tools were used
    if context:
        messages[-1]["content"] += context + "\nUse the tool results above."

    # Get Claude response
    response = await chat_with_claude(messages)
    state["final_response"] = response

    # Extract anime references
    pattern = r'\*\*([^*]+)\*\*'
    titles = re.findall(pattern, response)
    state["anime_references"] = [{"title": title} for title in titles]

    return state

# ============= BUILD GRAPH =============
def build_agent():
    """Build the LangGraph agent"""

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("decide", decide_node)
    graph.add_node("execute_tools", execute_tools_node)
    graph.add_node("respond", respond_node)

    # Add edges
    graph.set_entry_point("decide")
    graph.add_edge("decide", "execute_tools")
    graph.add_edge("execute_tools", "respond")
    graph.add_edge("respond", END)

    return graph.compile()

# Create agent instance
agent = build_agent()

# ============= PUBLIC API =============
async def run_agent(messages: list[dict]) -> dict:
    """
    Run the agent with a conversation history

    Args:
        messages: List of {"role": "user"/"assistant", "content": "..."} dicts

    Returns:
        {"response": "...", "tool_calls": [...], "anime_references": [...]}
    """

    state = AgentState(
        messages=messages,
        tool_calls=[],
        tool_results=[],
        final_response="",
        anime_references=[]
    )

    # Run agent
    result = await agent.ainvoke(state)

    return {
        "response": result["final_response"],
        "tool_calls": result["tool_calls"],
        "tool_results": result["tool_results"],
        "anime_references": result["anime_references"]
    }
