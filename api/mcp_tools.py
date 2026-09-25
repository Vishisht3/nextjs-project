from mcp.server.fastmcp import FastMCP
from sqlmodel import Session, select
from database import engine
from models import ResearchDocument

mcp_server = FastMCP("Biomedical Research Engine")

@mcp_server.tool()
def search_biomedical_records(query_keyword: str) -> str:
    """
    Search stored biomedical documents by keyword in title or content.
    """
    with Session(engine) as session:
        statement = select(ResearchDocument).where(
            ResearchDocument.title.contains(query_keyword) | 
            ResearchDocument.content.contains(query_keyword)
        )
        results = session.exec(statement).all()
        
        if not results:
            return f"No records found matching query: '{query_keyword}'"

        formatted_results = []
        for doc in results:
            status = "Processed" if doc.is_processed else "Processing"
            formatted_results.append(
                f"ID: {doc.id} | Title: {doc.title} | Status: {status}\nContent Excerpt: {doc.content[:200]}..."
            )
        return "\n---\n".join(formatted_results)