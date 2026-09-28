"""
config/loader.py
Configuration schemas and YAML loader for the RAG pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


@dataclass
class ChunkingConfig:
    min_tokens: int = 500
    max_tokens: int = 800
    overlap_tokens: int = 100
    tokenizer: str = "cl100k_base"


@dataclass
class EmbeddingConfig:
    provider: str = "local"
    model: str = "BAAI/bge-small-en-v1.5"
    dimensions: int = 384
    batch_size: int = 32


@dataclass
class VectorStoreConfig:
    backend: str = "postgres"
    postgres_url: str = "postgresql://postgres:postgrespassword@localhost:5432/research_rag"
    table_name: str = "document_embeddings"


@dataclass
class HybridConfig:
    enabled: bool = True
    vector_weight: float = 0.6
    bm25_weight: float = 0.4
    candidate_multiplier: int = 4


@dataclass
class RerankerConfig:
    enabled: bool = True
    model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_k_after_rerank: int = 5


@dataclass
class RetrievalConfig:
    top_k: int = 5
    score_threshold: float = 0.0
    include_metadata: bool = True
    hybrid: HybridConfig = field(default_factory=HybridConfig)
    reranker: RerankerConfig = field(default_factory=RerankerConfig)


@dataclass
class CitationEnforcementConfig:
    enabled: bool = True
    min_citations_required: int = 1
    citation_pattern: str = r"\[([A-Za-z0-9._-]+:\d+)\]"
    on_violation: str = "retry"
    max_retries: int = 2


@dataclass
class PromptsConfig:
    rag_system: str = "You are a precise research assistant. Answer using ONLY the provided context."
    rag_user: str = "Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    rag_retry: Optional[str] = None


@dataclass
class PipelineConfig:
    version: str = "2.0.0"
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    citation_enforcement: CitationEnforcementConfig = field(default_factory=CitationEnforcementConfig)
    prompts: PromptsConfig = field(default_factory=PromptsConfig)


def load_config(path: str = "config/phase2.yaml") -> PipelineConfig:
    p = Path(path)
    if not p.exists():
        return PipelineConfig()

    with open(p, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = yaml.safe_load(f) or {}

    chunking_data = data.get("chunking", {})
    chunking = ChunkingConfig(
        min_tokens=chunking_data.get("min_tokens", 500),
        max_tokens=chunking_data.get("max_tokens", 800),
        overlap_tokens=chunking_data.get("overlap_tokens", 100),
        tokenizer=chunking_data.get("tokenizer", "cl100k_base"),
    )

    embed_data = data.get("embedding", {})
    embedding = EmbeddingConfig(
        provider=embed_data.get("provider", "local"),
        model=embed_data.get("model", "BAAI/bge-small-en-v1.5"),
        dimensions=embed_data.get("dimensions", 384),
        batch_size=embed_data.get("batch_size", 32),
    )

    vs_data = data.get("vector_store", {})
    vector_store = VectorStoreConfig(
        backend=vs_data.get("backend", "postgres"),
        postgres_url=vs_data.get("postgres_url", "postgresql://postgres:postgrespassword@localhost:5432/research_rag"),
        table_name=vs_data.get("table_name", "document_embeddings"),
    )

    ret_data = data.get("retrieval", {})
    hyb_data = ret_data.get("hybrid", {})
    hybrid = HybridConfig(
        enabled=hyb_data.get("enabled", True),
        vector_weight=hyb_data.get("vector_weight", 0.6),
        bm25_weight=hyb_data.get("bm25_weight", 0.4),
        candidate_multiplier=hyb_data.get("candidate_multiplier", 4),
    )

    rerank_data = ret_data.get("reranker", {})
    reranker = RerankerConfig(
        enabled=rerank_data.get("enabled", True),
        model=rerank_data.get("model", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
        top_k_after_rerank=rerank_data.get("top_k_after_rerank", 5),
    )

    retrieval = RetrievalConfig(
        top_k=ret_data.get("top_k", 5),
        score_threshold=ret_data.get("score_threshold", 0.0),
        include_metadata=ret_data.get("include_metadata", True),
        hybrid=hybrid,
        reranker=reranker,
    )

    ce_data = data.get("citation_enforcement", {})
    citation_enforcement = CitationEnforcementConfig(
        enabled=ce_data.get("enabled", True),
        min_citations_required=ce_data.get("min_citations_required", 1),
        citation_pattern=ce_data.get("citation_pattern", r"\[([A-Za-z0-9._-]+:\d+)\]"),
        on_violation=ce_data.get("on_violation", "retry"),
        max_retries=ce_data.get("max_retries", 2),
    )

    prompt_data = data.get("prompts", {})
    prompts = PromptsConfig(
        rag_system=prompt_data.get("rag_system", "You are a precise research assistant."),
        rag_user=prompt_data.get("rag_user", "Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"),
        rag_retry=prompt_data.get("rag_retry"),
    )

    return PipelineConfig(
        version=data.get("version", "2.0.0"),
        chunking=chunking,
        embedding=embedding,
        vector_store=vector_store,
        retrieval=retrieval,
        citation_enforcement=citation_enforcement,
        prompts=prompts,
    )
