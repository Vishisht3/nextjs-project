"""
store/vector_store.py
Abstraction layer over PostgreSQL + pgvector database.

Uses psycopg (v3) — the modern Python PostgreSQL adapter with native async
support, binary protocol, and better performance vs the legacy psycopg2.
"""
from __future__ import annotations

import json
import os
from typing import List, Optional

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from config.loader import VectorStoreConfig
from ingestion.chunker import Chunk


class RetrievedChunk:
    """A chunk returned by a similarity search, decorated with a score."""

    def __init__(self, chunk_dict: dict, score: float):
        self.text: str          = chunk_dict["text"]
        self.doc_id: str        = chunk_dict["doc_id"]
        self.chunk_index: int   = chunk_dict["chunk_index"]
        self.source: str        = chunk_dict["source"]
        self.citation_id: str   = chunk_dict["citation_id"]
        self.token_count: int   = chunk_dict.get("token_count", 0)
        self.score: float       = score
        self.metadata: dict     = {
            k: v for k, v in chunk_dict.items()
            if k not in {"text", "doc_id", "chunk_index", "source",
                         "citation_id", "token_count"}
        }

    def __repr__(self) -> str:
        return (
            f"RetrievedChunk(citation={self.citation_id!r}, "
            f"score={self.score:.4f}, tokens={self.token_count})"
        )


class BaseVectorStore:
    def upsert(self, chunks: List[Chunk], embeddings: List[List[float]]) -> None:
        raise NotImplementedError

    def query(
        self,
        query_embedding: List[float],
        top_k: int,
        score_threshold: float = 0.0,
    ) -> List[RetrievedChunk]:
        raise NotImplementedError

    def delete_collection(self) -> None:
        raise NotImplementedError

    def count(self) -> int:
        raise NotImplementedError


class PostgresVectorStore(BaseVectorStore):
    """
    Persists chunks + embeddings in PostgreSQL using the pgvector extension.
    Uses Cosine distance (1 - cosine_distance) as similarity score.

    Uses psycopg v3 with:
      • row_factory=dict_row  (replaces psycopg2's RealDictCursor)
      • Context-manager connections for automatic cleanup
      • Binary protocol for better performance
    """

    def __init__(self, cfg: VectorStoreConfig):
        # Fall back to env var if not explicitly passed in config
        self.db_url = os.getenv(
            "DATABASE_URL",
            getattr(cfg, "postgres_url", "postgresql://postgres:postgrespassword@localhost:5432/research_rag")
        )
        self.table_name = "paper_chunks"
        self._ensure_schema()

    def _get_connection(self):
        conn = psycopg.connect(self.db_url, row_factory=dict_row)
        register_vector(conn)
        return conn

    def _ensure_schema(self) -> None:
        """Initializes extension, table schema, and HNSW cosine index."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id TEXT PRIMARY KEY,
                        doc_id TEXT NOT NULL,
                        chunk_index INT NOT NULL,
                        source TEXT NOT NULL,
                        citation_id TEXT NOT NULL,
                        token_count INT DEFAULT 0,
                        text TEXT NOT NULL,
                        metadata JSONB DEFAULT '{{}}'::jsonb,
                        embedding vector(384)
                    );
                """)
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_embedding
                    ON {self.table_name} USING hnsw (embedding vector_cosine_ops);
                """)
                conn.commit()

    def upsert(self, chunks: List[Chunk], embeddings: List[List[float]]) -> None:
        """
        Upserts chunks into Postgres.
        Key conflict on primary key `id` (doc_id + chunk_index) ensures idempotency.
        """
        if not chunks:
            return

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                for chunk, vector in zip(chunks, embeddings):
                    chunk_id = f"{chunk.doc_id}_{chunk.chunk_index}"
                    chunk_dict = chunk.to_dict()

                    # Separate core attributes from extra metadata
                    text = chunk_dict.pop("text", "")
                    doc_id = chunk_dict.pop("doc_id", "")
                    chunk_index = chunk_dict.pop("chunk_index", 0)
                    source = chunk_dict.pop("source", "")
                    citation_id = chunk_dict.pop("citation_id", "")
                    token_count = chunk_dict.pop("token_count", 0)
                    extra_metadata = json.dumps(chunk_dict)

                    cur.execute(
                        f"""
                        INSERT INTO {self.table_name}
                        (id, doc_id, chunk_index, source, citation_id, token_count, text, metadata, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            text = EXCLUDED.text,
                            metadata = EXCLUDED.metadata,
                            embedding = EXCLUDED.embedding;
                        """,
                        (
                            chunk_id,
                            doc_id,
                            chunk_index,
                            source,
                            citation_id,
                            token_count,
                            text,
                            extra_metadata,
                            vector
                        )
                    )
                conn.commit()

    def query(
        self,
        query_embedding: List[float],
        top_k: int,
        score_threshold: float = 0.0,
    ) -> List[RetrievedChunk]:
        """
        Queries top_k chunks ordered by cosine similarity.
        Cosine similarity = 1.0 - (embedding <=> query_embedding)
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT 
                        id, doc_id, chunk_index, source, citation_id, token_count, text, metadata,
                        1.0 - (embedding <=> %s) AS score
                    FROM {self.table_name}
                    ORDER BY embedding <=> %s ASC
                    LIMIT %s;
                    """,
                    (query_embedding, query_embedding, top_k)
                )
                rows = cur.fetchall()

            retrieved: List[RetrievedChunk] = []
            for row in rows:
                score = float(row["score"])
                if score < score_threshold:
                    continue

                chunk_dict = {
                    "text": row["text"],
                    "doc_id": row["doc_id"],
                    "chunk_index": row["chunk_index"],
                    "source": row["source"],
                    "citation_id": row["citation_id"],
                    "token_count": row["token_count"],
                    **(row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"] or "{}"))
                }
                retrieved.append(RetrievedChunk(chunk_dict, score))

            return retrieved

    def delete_collection(self) -> None:
        """Truncates the table."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"TRUNCATE TABLE {self.table_name};")
                conn.commit()

    def count(self) -> int:
        """Returns total chunk count in table."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) as cnt FROM {self.table_name};")
                result = cur.fetchone()
                return result["cnt"] if result else 0


def build_vector_store(cfg: VectorStoreConfig) -> BaseVectorStore:
    """Builds and returns the PostgreSQL pgvector vector store."""
    return PostgresVectorStore(cfg)