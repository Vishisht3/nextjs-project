"""
ingestion/embedder.py
Converts text chunks into 384-dimensional embedding vectors using fastembed (ONNX Runtime).
"""

from __future__ import annotations

from typing import List

from config.loader import EmbeddingConfig
from ingestion.chunker import Chunk


class BaseEmbedder:
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

    def embed_chunks(self, chunks: List[Chunk]) -> List[List[float]]:
        return self.embed_texts([c.text for c in chunks])

    def embed_query(self, query: str) -> List[float]:
        return self.embed_texts([query])[0]


class LocalEmbedder(BaseEmbedder):
    """
    Server-side CPU embedder using fastembed (ONNX Runtime).
    Uses BAAI/bge-small-en-v1.5 by default.
    """

    DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"

    def __init__(self, cfg: EmbeddingConfig):
        try:
            from fastembed import TextEmbedding
        except ImportError:
            raise ImportError("Run: pip install fastembed")

        model_name = getattr(cfg, "model", self.DEFAULT_MODEL) or self.DEFAULT_MODEL
        self.batch_size = getattr(cfg, "batch_size", 32)

        self.model = TextEmbedding(model_name=model_name)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        # fastembed.embed() generates numpy arrays; convert to float lists
        embeddings = list(self.model.embed(texts, batch_size=self.batch_size))
        return [emb.tolist() for emb in embeddings]


def build_embedder(cfg: EmbeddingConfig) -> BaseEmbedder:
    """Return fastembed-based in-process server embedder."""
    return LocalEmbedder(cfg)