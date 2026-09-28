"""
mcp_server/server.py
MCP server wrapper around agent/tools.py.
Uses the MCP SDK v2 MCPServer class.
"""
from mcp.server import MCPServer

mcp = MCPServer("CS-Research-Assistant")

from agent.tools import retrieve_chunks, knowledge_base_status


@mcp.tool()
def search_research_papers(query: str) -> str:
    """Performs hybrid search across CS and AI research paper chunks."""
    result = retrieve_chunks(query)
    return result["context_block"]


@mcp.tool()
def check_knowledge_base() -> str:
    """Returns the current indexing status and chunk count of the knowledge base."""
    import json
    return json.dumps(knowledge_base_status())


if __name__ == "__main__":
    mcp.run()