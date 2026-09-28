"""
api/main.py
FastAPI application for the CS & AI Research Assistant RAG Engine.
Streams ReAct Agent reasoning traces and tokens via Server-Sent Events (SSE).
"""
import asyncio
import json
import os
import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.loop import AgenticRAGLoop

agent_loop: AgenticRAGLoop | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[API] Initializing Agentic RAG Loop...")
    global agent_loop
    agent_loop = AgenticRAGLoop()
    yield
    print("[API] Shutting down service...")


app = FastAPI(
    title="CS & AI Research Assistant RAG Engine",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DocumentUpload(BaseModel):
    title: str
    content: str


class QueryRequest(BaseModel):
    prompt: str


@app.get("/health")
def health_check():
    return {
        "status": "System Online",
        "agent_initialized": agent_loop is not None,
    }


@app.post("/documents/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(payload: DocumentUpload):
    """Ingest plain document text into the vector store and BM25 index."""
    try:
        from ingestion.pipeline import build_ingestion_pipeline

        pipeline, _ = build_ingestion_pipeline("config/phase2.yaml")
        stats = pipeline.ingest_documents([{
            "text": payload.content,
            "source": payload.title,
            "metadata": {"title": payload.title},
        }])
        return {
            "message": "Document successfully ingested into knowledge base",
            "chunks_created": stats.num_chunks,
        }
    except Exception as exc:
        return {
            "message": "Ingestion failed or database offline",
            "error": str(exc),
        }


@app.post("/documents/upload-file", status_code=status.HTTP_201_CREATED)
async def upload_file(file: UploadFile = File(...)):
    """Ingest a PDF, DOCX, PPTX, TeX, or TXT upload."""
    if not file.filename:
        return {"message": "No file provided", "error": "Missing filename"}

    allowed_extensions = {".pdf", ".docx", ".pptx", ".tex", ".txt"}
    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{suffix or 'none'}'. Allowed: PDF, DOCX, PPTX, TeX, TXT.",
        )

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        from ingestion.pipeline import build_ingestion_pipeline

        pipeline, _ = build_ingestion_pipeline("config/phase2.yaml")
        stats = pipeline.ingest_file(
            tmp_path,
            metadata={"title": file.filename, "original_filename": file.filename},
        )
        return {
            "message": f"File '{file.filename}' successfully ingested",
            "chunks_created": stats.num_chunks,
            "documents_processed": stats.num_documents,
            "elapsed_seconds": round(stats.elapsed_seconds, 2),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": f"Failed to ingest '{file.filename}'", "error": str(exc)},
        ) from exc
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@app.get("/agent/stream")
async def agent_stream(query: str = Query(..., description="Research question or paper query")):
    """Stream ReAct tool traces, verifier results, and the final answer."""
    if agent_loop is None:
        raise HTTPException(status_code=500, detail="Agent loop is not initialized.")

    async def sse_generator():
        async for event in agent_loop.run_stream(query):
            event_type = event["event"]
            data_str = json.dumps(event["data"])
            yield f"event: {event_type}\ndata: {data_str}\n\n"
            await asyncio.sleep(0.001)

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
