"""
retrieval/reranker.py
Cross-encoder re-ranker using fastembed (ONNX Runtime).

A cross-encoder scores (query, passage) pairs jointly, which is far more
accurate than the inner-product approximation used in bi-encoder retrieval.
The trade-off is speed — O(k) inference calls — so we only re-rank a small
candidate set (top_k × candidate_multiplier from Phase 2 config).

Model used:  Xenova/ms-marco-MiniLM-L-6-v2
  • ONNX-optimized version of the MS MARCO cross-encoder
  • ~22 M parameters — fast on CPU, sub-second for 20 candidates
  • No PyTorch dependency — uses fastembed's TextCrossEncoder (ONNX Runtime)
  • Swap to a larger model in config/phase2.yaml without code changes
"""
from __future__ import annotations

import math
from typing import List

from store.vector_store import RetrievedChunk


class CrossEncoderReranker:
    """
    Wraps fastembed's TextCrossEncoder for ONNX-based re-ranking.
    Lazy-loaded on first use to avoid import overhead when re-ranking
    is disabled via config.
    """

    # fastembed uses the Xenova/ prefix for ONNX cross-encoder models
    MODEL_MAP = {
        "cross-encoder/ms-marco-MiniLM-L-6-v2": "Xenova/ms-marco-MiniLM-L-6-v2",
    }

    def __init__(self, model_name: str):
        # Map sentence-transformers model names to fastembed equivalents
        self.model_name = self.MODEL_MAP.get(model_name, model_name)
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from fastembed.rerank.cross_encoder import TextCrossEncoder
            except ImportError:
                raise ImportError(
                    "Run: pip install fastembed\n"
                    "Or disable re-ranking in config: reranker.enabled = false"
                )
            self._model = TextCrossEncoder(model_name=self.model_name)

    def rerank(
        self,
        query: str,
        candidates: List[RetrievedChunk],
        top_k: int,
    ) -> List[RetrievedChunk]:
        """
        Score each (query, chunk.text) pair and return the top_k highest-
        scoring chunks, with their score replaced by the cross-encoder score
        (normalised to [0, 1] via sigmoid).

        Args:
            query:      The user's original question.
            candidates: Candidate chunks from hybrid retrieval.
            top_k:      How many to return after re-ranking.

        Returns:
            Sorted list of RetrievedChunk, best first.
        """
        if not candidates:
            return []

        self._load()

        documents = [chunk.text for chunk in candidates]
        raw_scores: List[float] = list(self._model.rerank(query, documents))

        def sigmoid(x: float) -> float:
            return 1.0 / (1.0 + math.exp(-x))

        for chunk, raw in zip(candidates, raw_scores):
            chunk.score = sigmoid(raw)

        reranked = sorted(candidates, key=lambda c: c.score, reverse=True)
        return reranked[:top_k]