"""
retrieval/bm25_index.py
Sparse keyword search using BM25 (bm25s — modern, high-performance BM25).

The index is built in-memory from the chunks stored in PostgreSQL.
It is rebuilt on process start or post-ingestion.

Interface mirrors BaseVectorStore.query() so the hybrid layer can treat
both retrievers identically.

Uses bm25s (2025+) instead of the legacy rank-bm25 library for:
  • Scipy sparse matrix scoring (orders of magnitude faster)
  • Built-in stemming and stopword support
  • Better memory efficiency for large corpora
"""
from __future__ import annotations

import json
import string
from typing import List, Optional

from ingestion.chunker import Chunk
from store.vector_store import RetrievedChunk


class BM25Index:
    """
    In-memory BM25 index over a fixed corpus of chunks.

    Build once after ingestion; rebuild whenever new docs are added.
    """

    def __init__(self):
        self._chunks: List[Chunk] = []
        self._retriever = None
        self._corpus_tokens = None

    def build(self, chunks: List[Chunk]) -> None:
        """
        (Re)build the BM25 index over the given chunks.
        Call this after every ingestion run.
        """
        try:
            import bm25s
        except ImportError:
            raise ImportError("Run: pip install bm25s")

        self._chunks = chunks
        corpus = [c.text for c in chunks]

        # Tokenize the corpus using bm25s built-in tokenizer
        self._corpus_tokens = bm25s.tokenize(corpus, stopwords="en")

        # Create and index the retriever
        self._retriever = bm25s.BM25()
        self._retriever.index(self._corpus_tokens)

    def build_from_vector_store(self, vector_store) -> None:
        """
        Pull all chunks out of the PostgreSQL vector store and build the index.
        """
        conn = vector_store._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT text, doc_id, chunk_index, source, citation_id, token_count, metadata FROM {vector_store.table_name};"
                )
                rows = cur.fetchall()

            chunks = []
            for row in rows:
                chunk_dict = {
                    "text": row["text"],
                    "doc_id": row["doc_id"],
                    "chunk_index": row["chunk_index"],
                    "source": row["source"],
                    "citation_id": row["citation_id"],
                    "token_count": row["token_count"],
                    **(row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"] or "{}"))
                }
                chunks.append(_dict_to_chunk(chunk_dict))
            self.build(chunks)
        finally:
            conn.close()

    def query(
        self,
        query_text: str,
        top_k: int,
        score_threshold: float = 0.0,
    ) -> List[RetrievedChunk]:
        """
        Return top_k chunks ranked by BM25 score.
        Scores are normalized to [0, 1] relative to the highest score in
        this query so they can be combined with cosine similarity scores.
        """
        if self._retriever is None or not self._chunks:
            return []

        try:
            import bm25s
        except ImportError:
            return []

        query_tokens = bm25s.tokenize(query_text, stopwords="en")

        # Retrieve top_k results — returns (doc_indices, scores) arrays
        doc_indices, scores = self._retriever.retrieve(
            query_tokens, corpus=self._chunks, k=min(top_k, len(self._chunks))
        )

        # doc_indices and scores are 2D arrays (one row per query)
        indices_row = doc_indices[0]
        scores_row = scores[0]

        max_score = max(scores_row) if len(scores_row) > 0 and max(scores_row) > 0 else 1.0

        results: List[RetrievedChunk] = []
        for idx, score in zip(indices_row, scores_row):
            norm_score = float(score) / float(max_score)
            if norm_score < score_threshold:
                continue
            chunk = self._chunks[int(idx)] if not isinstance(idx, Chunk) else idx
            results.append(RetrievedChunk(chunk.to_dict(), score=norm_score))

        return results

    @staticmethod
    def _tokenise(text: str) -> List[str]:
        """
        Lowercase, strip punctuation, split on whitespace.
        Kept as a fallback — bm25s has its own built-in tokenizer.
        """
        text = text.lower()
        text = text.translate(str.maketrans("", "", string.punctuation))
        return text.split()


def _dict_to_chunk(d: dict) -> Chunk:
    from ingestion.chunker import Chunk
    return Chunk(
        text        = d.get("text", ""),
        doc_id      = d.get("doc_id", ""),
        chunk_index = int(d.get("chunk_index", 0)),
        source      = d.get("source", ""),
        token_count = int(d.get("token_count", 0)),
        start_token = int(d.get("start_token", 0)),
        end_token   = int(d.get("end_token", 0)),
        metadata    = {
            k: v for k, v in d.items()
            if k not in {"text", "doc_id", "chunk_index", "source",
                         "token_count", "start_token", "end_token", "citation_id"}
        },
    )