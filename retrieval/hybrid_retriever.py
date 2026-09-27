"""
retrieval/hybrid_retriever.py
Unified retriever combining dense semantic vector search, BM25 sparse keyword search,
cross-encoder re-ranking, and inline citation enforcement.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from config.loader import PipelineConfig
from ingestion.embedder import BaseEmbedder
from retrieval.bm25_index import BM25Index
from retrieval.citation_enforcer import CitationEnforcer
from retrieval.reranker import CrossEncoderReranker
from store.vector_store import BaseVectorStore, RetrievedChunk


@dataclass
class RetrievalResult:
    query: str
    chunks: List[RetrievedChunk]
    context_block: str
    citations: List[str]


@dataclass
class RAGAnswer:
    question: str
    answer: str
    retrieved_chunks: List[RetrievedChunk]
    citations: List[str]
    context_block: str


class HybridRetriever:
    """
    Unified retriever supporting dense vector search, optional BM25 hybrid fusion,
    cross-encoder re-ranking, and citation verification.
    """

    def __init__(
        self,
        embedder: BaseEmbedder,
        vector_store: BaseVectorStore,
        cfg: PipelineConfig,
        bm25_index: Optional[BM25Index] = None,
    ):
        self.embedder = embedder
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.cfg = cfg

        rc = cfg.retrieval
        self.reranker = (
            CrossEncoderReranker(rc.reranker.model)
            if rc.reranker.enabled
            else None
        )
        self.enforcer = CitationEnforcer(cfg.citation_enforcement)

    def retrieve(self, query: str) -> RetrievalResult:
        rc = self.cfg.retrieval
        use_hybrid = rc.hybrid.enabled and self.bm25_index is not None

        n_candidates = rc.top_k * rc.hybrid.candidate_multiplier if use_hybrid else rc.top_k

        query_embedding = self.embedder.embed_query(query)
        vector_chunks = self.vector_store.query(
            query_embedding=query_embedding,
            top_k=n_candidates,
            score_threshold=rc.score_threshold,
        )

        if use_hybrid:
            bm25_chunks = self.bm25_index.query(query, top_k=n_candidates)
            candidates = self._fuse(
                vector_chunks,
                bm25_chunks,
                alpha=rc.hybrid.vector_weight,
            )
        else:
            candidates = vector_chunks

        if self.reranker is not None:
            final_chunks = self.reranker.rerank(
                query=query,
                candidates=candidates,
                top_k=rc.reranker.top_k_after_rerank,
            )
        else:
            final_chunks = candidates[: rc.top_k]

        context_block, citations = self._format_context(final_chunks)

        return RetrievalResult(
            query=query,
            chunks=final_chunks,
            context_block=context_block,
            citations=citations,
        )

    def _format_context(self, chunks: List[RetrievedChunk]) -> Tuple[str, List[str]]:
        blocks: List[str] = []
        citations: List[str] = []

        for chunk in chunks:
            cid = chunk.citation_id
            citations.append(cid)
            blocks.append(f"[{cid}] (source: {chunk.source})\n{chunk.text}")

        context_str = "\n\n---\n\n".join(blocks)
        return context_str, citations

    def build_prompt(self, result: RetrievalResult) -> Tuple[str, str]:
        prompts = self.cfg.prompts
        system_prompt = prompts.rag_system
        user_prompt = prompts.rag_user.format(
            context=result.context_block,
            question=result.query,
        )
        return system_prompt, user_prompt

    def build_retry_prompt(
        self,
        result: RetrievalResult,
        previous_answer: str,
    ) -> Tuple[str, str]:
        prompts = self.cfg.prompts
        retry_template = getattr(prompts, "rag_retry", None) or prompts.rag_user

        user_prompt = retry_template.format(
            context=result.context_block,
            question=result.query,
            previous_answer=previous_answer,
        )
        return prompts.rag_system, user_prompt

    @staticmethod
    def _fuse(
        vector_chunks: List[RetrievedChunk],
        bm25_chunks: List[RetrievedChunk],
        alpha: float,
    ) -> List[RetrievedChunk]:
        """
        Weighted score fusion:
            fused_score = alpha * vector_score + (1 - alpha) * bm25_score
        """
        vec_map: Dict[str, Tuple[RetrievedChunk, float]] = {
            c.citation_id: (c, c.score) for c in vector_chunks
        }
        bm25_map: Dict[str, float] = {
            c.citation_id: c.score for c in bm25_chunks
        }

        all_ids = set(vec_map.keys()) | set(bm25_map.keys())

        fused: List[Tuple[float, RetrievedChunk]] = []
        for cid in all_ids:
            if cid in vec_map:
                chunk, vec_score = vec_map[cid]
            else:
                bm25_chunk = next(c for c in bm25_chunks if c.citation_id == cid)
                chunk, vec_score = bm25_chunk, 0.0

            bm25_score = bm25_map.get(cid, 0.0)
            score = alpha * vec_score + (1.0 - alpha) * bm25_score
            chunk.score = score
            fused.append((score, chunk))

        fused.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in fused]


class HybridRAGPipeline:
    """
    Full RAG pipeline using Groq:
        HybridRetriever → Groq LLM generation → CitationEnforcer (with retry)
    """

    def __init__(self, retriever: HybridRetriever, cfg: PipelineConfig):
        self.retriever = retriever
        self.cfg = cfg
        self._llm = self._init_llm()

    def _init_llm(self):
        try:
            from groq import Groq
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                return None
            return Groq(api_key=api_key)
        except Exception:
            return None

    def answer(self, question: str, model: Optional[str] = None) -> RAGAnswer:
        if self._llm is None:
            raise RuntimeError("Groq LLM client not initialised. Check GROQ_API_KEY environment variable.")

        target_model = model or os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
        result = self.retriever.retrieve(question)
        system, user = self.retriever.build_prompt(result)

        def _call_llm(system_p: str, user_p: str) -> str:
            resp = self._llm.chat.completions.create(
                model=target_model,
                messages=[
                    {"role": "system", "content": system_p},
                    {"role": "user",   "content": user_p},
                ],
                temperature=0.0,
            )
            return resp.choices[0].message.content or ""

        answer_text = _call_llm(system, user)

        def _retry_fn(prev_answer: str) -> str:
            retry_system, retry_user = self.retriever.build_retry_prompt(
                result, prev_answer
            )
            return _call_llm(retry_system, retry_user)

        check = self.retriever.enforcer.enforce(
            answer=answer_text,
            retrieved_chunks=result.chunks,
            retry_fn=_retry_fn,
        )

        return RAGAnswer(
            question=question,
            answer=check.answer,
            retrieved_chunks=result.chunks,
            citations=result.citations,
            context_block=result.context_block,
        )


# Zero-redundancy aliases
Retriever = HybridRetriever
RAGPipeline = HybridRAGPipeline