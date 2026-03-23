from __future__ import annotations

import os
import asyncio
from typing import Any, Dict, TypedDict, Annotated, Optional

from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages

from langchain_mcp_adapters.client import MultiServerMCPClient

if "GOOGLE_API_KEY" not in os.environ:
    print("Warning: GOOGLE_API_KEY not found in environment variables.")

# ----------------------------
# State
# ----------------------------
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


SYSTEM_PROMPT = """#Role: You are a resume writing assistant.
#Task: Improve resume bullet points using the resume_bullet_tool when rewriting is needed.
#Topic: Resume bullets (impact, clarity, metrics).
#Format: Provide:
1) Improved bullet (best)
2) 2 alternative variants
3) Quick score (0-10) and what to improve next
#Tone / Style: Professional, confident, and concise.
#Context: You have access to resume_bullet_tool(bullet, target_role) which returns variants and a score.
#Goal: Produce stronger, metric-oriented bullets aligned with the target role.
#Requirements / Constraints:
Use resume_bullet_tool for rewriting or scoring bullets.
Do not fabricate metrics; if missing, ask the user to supply numbers or include placeholders.
Keep bullets to ~1-2 lines.
"""


# ----------------------------
# Graph factory (async because MCP tool loading is async)
# ----------------------------
async def make_graph() -> Any:
    # This is the beginning of the MCP Client
    mcp_url = os.getenv("MCP_TOOL_URL", "http://localhost:9000/mcp")

    # MCP client -> load tools from FastMCP server
    client = MultiServerMCPClient(
        {
            "resume_tools": {
                "transport": "http",
                "url": mcp_url,
            }
        }
    )
    tools = await client.get_tools()  # Converts MCP tools into LangChain tools :contentReference[oaicite:2]{index=2}
    # This is the end of the MCP Client
    llm = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"),
        temperature=0.2,
    ).bind_tools(tools)

    tool_node = ToolNode(tools)

    def llm_node(state: AgentState) -> Dict[str, Any]:
        msgs = state["messages"]
        if not msgs or msgs[0].type != "system":
            msgs = [SystemMessage(content=SYSTEM_PROMPT)] + msgs
        resp = llm.invoke(msgs)
        return {"messages": [resp]}

    g = StateGraph(AgentState)
    g.add_node("llm", llm_node)
    g.add_node("tools", tool_node)

    g.set_entry_point("llm")
    g.add_conditional_edges("llm", tools_condition, {"tools": "tools", END: END})
    g.add_edge("tools", "llm")

    return g.compile()


# ----------------------------
# Cached graph instance
# ----------------------------
_GRAPH: Optional[Any] = None


async def get_graph() -> Any:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = await make_graph()
    return _GRAPH


def content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Gemini often returns a list of parts: [{"type":"text","text":"..."}]
        texts = []
        for part in content:
            if isinstance(part, dict):
                if "text" in part and isinstance(part["text"], str):
                    texts.append(part["text"])
            elif isinstance(part, str):
                texts.append(part)
        return "\n".join(t.strip() for t in texts if t.strip())
    if isinstance(content, dict):
        # Sometimes content can be {"text": "..."}
        if "text" in content and isinstance(content["text"], str):
            return content["text"]
    return str(content)


async def run_agent_async(user_query: str) -> str:
    graph = await get_graph()
    out = await graph.ainvoke({"messages": [{"role": "user", "content": user_query}]})
    last = out["messages"][-1]
    return content_to_text(getattr(last, "content", last))


def run_agent(user_query: str) -> str:
    """Sync wrapper (handy for scripts)."""
    return asyncio.run(run_agent_async(user_query))


if __name__ == "__main__":
    q = "Rewrite this resume bullet for a Data Engineer role: 'worked on pipelines and data stuff for the team'"
    print(run_agent(q))