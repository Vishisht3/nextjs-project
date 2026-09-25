from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel import Session, select
from contextlib import asynccontextmanager
from pydantic import BaseModel
from database import init_db, get_session
from models import ResearchDocument
from worker import enqueue_document_processing
from mcp_tools import search_biomedical_records

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing Database...")
    init_db()
    yield
    print("Shutting down...")

app = FastAPI(title="Biomedical RAG Orchestrator", lifespan=lifespan)

class DocumentUpload(BaseModel):
    title: str
    content: str

@app.get("/health")
def health_check():
    return {"status": "System Online", "mcp_ready": True}

@app.get("/documents")
def list_documents(session: Session = Depends(get_session)):
    return session.exec(select(ResearchDocument)).all()

@app.post("/documents/upload", status_code=status.HTTP_201_CREATED)
def upload_document(payload: DocumentUpload, session: Session = Depends(get_session)):
    """
    Store document metadata and offload processing to the worker thread pool.
    """
    doc = ResearchDocument(title=payload.title, content=payload.content, is_processed=False)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    enqueue_document_processing(doc.id)

    return {
        "message": "Document accepted and queued for background indexing.",
        "doc_id": doc.id,
        "is_processed": False
    }

@app.get("/mcp/test-query")
def test_mcp_tool(keyword: str):
    """Direct HTTP route to test the MCP tool's database search capability."""
    return {"result": search_biomedical_records(keyword)}