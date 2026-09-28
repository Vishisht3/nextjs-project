"""
agent/tools.py
Tool implementations for the Agentic RAG ReAct loop and MCP server.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

_retriever = None
_pipeline = None


def get_retriever():
    global _retriever, _pipeline
    if _retriever is None:
        try:
            from ingestion.pipeline import build_ingestion_pipeline
            config_path = os.getenv("RAG_CONFIG", "config/phase2.yaml")
            _pipeline, bundle = build_ingestion_pipeline(config_path)
            _retriever = bundle.retriever
        except Exception as e:
            print(f"[agent.tools] Warning: Could not initialize retriever ({e})")
            _retriever = None
    return _retriever


def fetch_and_ingest_arxiv(query: str, max_results: int = 1) -> Dict[str, Any]:
    """Find an arXiv paper, ingest its abstract, and return its citation metadata."""
    if not query.strip():
        return {"status": "error", "message": "A paper title, author, or concept is required."}

    try:
        params = urllib.parse.urlencode({
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max(1, min(max_results, 3)),
            "sortBy": "relevance",
        })
        request = urllib.request.Request(
            f"https://export.arxiv.org/api/query?{params}",
            headers={"User-Agent": "CSResearchAssistant/1.0"},
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            root = ET.fromstring(response.read())

        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", namespace)
        if not entries:
            return {"status": "not_found", "query": query, "papers": []}

        from ingestion.pipeline import build_ingestion_pipeline
        global _pipeline, _retriever
        if _pipeline is None:
            _pipeline, bundle = build_ingestion_pipeline(os.getenv("RAG_CONFIG", "config/phase2.yaml"))
            _retriever = bundle.retriever

        papers = []
        for entry in entries:
            paper_url = (entry.findtext("atom:id", default="", namespaces=namespace)).strip()
            title = " ".join((entry.findtext("atom:title", default="", namespaces=namespace)).split())
            abstract = " ".join((entry.findtext("atom:summary", default="", namespaces=namespace)).split())
            arxiv_id = paper_url.rsplit("/", 1)[-1]
            authors = [
                author.findtext("atom:name", default="", namespaces=namespace)
                for author in entry.findall("atom:author", namespace)
            ]
            _pipeline.ingest_documents([{
                "text": f"Title: {title}\nAuthors: {', '.join(authors)}\nAbstract: {abstract}",
                "source": paper_url or f"arXiv:{arxiv_id}",
                "metadata": {"title": title, "authors": authors, "arxiv_id": arxiv_id, "url": paper_url, "format": "arxiv"},
            }])
            papers.append({"arxiv_id": arxiv_id, "title": title, "url": paper_url})

        return {"status": "ingested", "query": query, "papers": papers}
    except Exception as exc:
        return {"status": "error", "query": query, "message": str(exc), "papers": []}


class _DuckDuckGoParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results: List[Dict[str, str]] = []
        self._current: Optional[Dict[str, str]] = None
        self._field: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        if tag == "a" and "result__a" in classes:
            self._current = {"url": attributes.get("href", ""), "title": ""}
            self._field = "title"
        elif self._current and tag == "a" and "result__snippet" in classes:
            self._field = "snippet"

    def handle_data(self, data: str) -> None:
        if self._current and self._field:
            self._current[self._field] = self._current.get(self._field, "") + data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current and self._field == "snippet":
            self.results.append(self._current)
            self._current = None
            self._field = None


def search_web(query: str, max_results: int = 3) -> Dict[str, Any]:
    """Search DuckDuckGo's HTML endpoint and ingest result snippets as evidence."""
    if not query.strip():
        return {"status": "error", "message": "A search query is required.", "results": []}

    try:
        url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
        request = urllib.request.Request(url, headers={"User-Agent": "CSResearchAssistant/1.0"})
        with urllib.request.urlopen(request, timeout=15) as response:
            parser = _DuckDuckGoParser()
            parser.feed(response.read().decode("utf-8", errors="replace"))

        from ingestion.pipeline import build_ingestion_pipeline
        global _pipeline, _retriever
        if _pipeline is None:
            _pipeline, bundle = build_ingestion_pipeline(os.getenv("RAG_CONFIG", "config/phase2.yaml"))
            _retriever = bundle.retriever

        results = []
        for item in parser.results[:max(1, min(max_results, 5))]:
            title = " ".join(item.get("title", "").split())
            snippet = " ".join(item.get("snippet", "").split())
            result_url = item.get("url", "")
            if not title or not snippet:
                continue
            _pipeline.ingest_documents([{
                "text": f"Title: {title}\nSource: {result_url}\nSummary: {snippet}",
                "source": result_url or title,
                "metadata": {"title": title, "url": result_url, "format": "web_search"},
            }])
            results.append({"title": title, "url": result_url, "snippet": snippet})

        return {"status": "ingested", "query": query, "results": results}
    except Exception as exc:
        return {"status": "error", "query": query, "message": str(exc), "results": []}


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
