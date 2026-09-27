"""
api/main.py
FastAPI application for the CS & AI Research Assistant RAG Engine.
Streams ReAct Agent reasoning traces and tokens via Server-Sent Events (SSE).
"""
import asyncio
from contextlib import asynccontextmanager
import json
from fastapi import FastAPI, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.loop import AgenticRAGLoop

agent_loop: AgenticRAGLoop = None


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
    """
    Ingests research paper texts directly into the vector store and BM25 index.
    """
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
    except Exception as e:
        return {
            "message": "Ingestion failed or database offline",
            "error": str(e),
        }


@app.get("/agent/stream")
async def agent_stream(query: str = Query(..., description="Research question or paper query")):
    """
    Streams the 4-iteration ReAct Agent loop using Server-Sent Events (SSE).
    Emits events: tool_call, chunk_result, verifier, final_answer.
    """
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