"""
agent/tools.py
Tool implementations for the Agentic RAG ReAct loop and MCP server.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import os

_retriever = None


def get_retriever():
    global _retriever
    if _retriever is None:
        try:
            from ingestion.pipeline import build_ingestion_pipeline
            config_path = os.getenv("RAG_CONFIG", "config/phase2.yaml")
            _, bundle = build_ingestion_pipeline(config_path)
            _retriever = bundle.retriever
        except Exception as e:
            print(f"[agent.tools] Warning: Could not initialize retriever ({e})")
            _retriever = None
    return _retriever


def retrieve_chunks(query: str, top_k: Optional[int] = None) -> Dict[str, Any]:
    """
    Performs hybrid BM25 + dense vector search across paper chunks.
    Returns context_block and structured chunk metadata.
    """
    retriever = get_retriever()
    if retriever is None:
        return {
            "context_block": "Knowledge base retriever currently unavailable (database connection pending).",
            "citations": [],
            "chunks": [],
        }

    try:
        result = retriever.retrieve(query)
        chunks_data: List[Dict[str, Any]] = []
        for c in result.chunks:
            chunks_data.append({
                "citation_id": c.citation_id,
                "doc_id": c.doc_id,
                "chunk_index": c.chunk_index,
                "source": c.source,
                "score": c.score,
                "text": c.text,
                "metadata": c.metadata,
            })

        return {
            "context_block": result.context_block,
            "citations": result.citations,
            "chunks": chunks_data,
        }
    except Exception as e:
        return {
            "context_block": f"Retrieval error: {e}",
            "citations": [],
            "chunks": [],
        }


def knowledge_base_status() -> Dict[str, Any]:
    """
    Checks the status and number of indexed chunks in the vector store.
    """
    retriever = get_retriever()
    if retriever is None or retriever.vector_store is None:
        return {
            "status": "unconnected",
            "indexed_chunks": 0,
            "message": "Vector store not connected.",
        }

    try:
        count = retriever.vector_store.count()
        return {
            "status": "online",
            "indexed_chunks": count,
            "backend": getattr(retriever.vector_store, "backend", "postgres"),
        }
    except Exception as e:
        return {
            "status": "error",
            "indexed_chunks": 0,
            "error": str(e),
        }
