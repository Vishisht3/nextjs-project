"""
ingestion/chunker.py
Token-based chunking with citation and metadata tracking.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Dict, List, Optional

from config.loader import ChunkingConfig


@dataclass
class Chunk:
    text: str
    doc_id: str
    chunk_index: int
    source: str
    token_count: int = 0
    start_token: int = 0
    end_token: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def citation_id(self) -> str:
        return f"{self.doc_id}:{self.chunk_index}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "doc_id": self.doc_id,
            "chunk_index": self.chunk_index,
            "source": self.source,
            "citation_id": self.citation_id,
            "token_count": self.token_count,
            "start_token": self.start_token,
            "end_token": self.end_token,
            **self.metadata,
        }


class TokenChunker:
    """
    Splits document texts into token-bounded chunks with sliding window overlap.
    Uses tiktoken if installed; falls back to robust whitespace splitting.
    """

    def __init__(self, cfg: Optional[ChunkingConfig] = None):
        self.cfg = cfg or ChunkingConfig()
        self._tokenizer = None
        self._init_tokenizer()

    def _init_tokenizer(self):
        try:
            import tiktoken
            self._tokenizer = tiktoken.get_encoding(self.cfg.tokenizer)
        except Exception:
            self._tokenizer = None

    def _count_tokens(self, text: str) -> int:
        if self._tokenizer:
            return len(self._tokenizer.encode(text))
        return len(text.split())

    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Chunk]:
        all_chunks: List[Chunk] = []

        for doc in documents:
            text = doc.get("text", "")
            source = doc.get("source", "unknown")
            doc_id = doc.get("doc_id") or hashlib.sha256((source + text[:100]).encode("utf-8")).hexdigest()[:12]
            doc_meta = doc.get("metadata", {})

            if not text.strip():
                continue

            # Tokenize or word-tokenize
            if self._tokenizer:
                tokens = self._tokenizer.encode(text)
                total_tokens = len(tokens)
                step = max(1, self.cfg.max_tokens - self.cfg.overlap_tokens)

                for chunk_idx, start_idx in enumerate(range(0, total_tokens, step)):
                    end_idx = min(start_idx + self.cfg.max_tokens, total_tokens)
                    chunk_tokens = tokens[start_idx:end_idx]
                    chunk_text = self._tokenizer.decode(chunk_tokens)

                    all_chunks.append(
                        Chunk(
                            text=chunk_text,
                            doc_id=doc_id,
                            chunk_index=chunk_idx,
                            source=source,
                            token_count=len(chunk_tokens),
                            start_token=start_idx,
                            end_token=end_idx,
                            metadata=doc_meta.copy(),
                        )
                    )
            else:
                words = text.split()
                total_words = len(words)
                step = max(1, self.cfg.max_tokens - self.cfg.overlap_tokens)

                for chunk_idx, start_idx in enumerate(range(0, total_words, step)):
                    end_idx = min(start_idx + self.cfg.max_tokens, total_words)
                    chunk_words = words[start_idx:end_idx]
                    chunk_text = " ".join(chunk_words)

                    all_chunks.append(
                        Chunk(
                            text=chunk_text,
                            doc_id=doc_id,
                            chunk_index=chunk_idx,
                            source=source,
                            token_count=len(chunk_words),
                            start_token=start_idx,
                            end_token=end_idx,
                            metadata=doc_meta.copy(),
                        )
                    )

        return all_chunks
