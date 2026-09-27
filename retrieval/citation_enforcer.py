"""
retrieval/citation_enforcer.py
Verifies that generated answers cite retrieved chunk IDs properly.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, List, Optional

from config.loader import CitationEnforcementConfig
from store.vector_store import RetrievedChunk


@dataclass
class CitationCheckResult:
    is_valid: bool
    answer: str
    found_citations: List[str]
    retries_used: int = 0
    reason: Optional[str] = None


class CitationEnforcer:
    """
    Validates that claims in the answer carry citations matching retrieved chunks.
    If citations are missing, optionally prompts the LLM retry callback.
    """

    def __init__(self, cfg: CitationEnforcementConfig):
        self.cfg = cfg
        self.pattern = re.compile(cfg.citation_pattern)

    def extract_citations(self, text: str) -> List[str]:
        return self.pattern.findall(text)

    def enforce(
        self,
        answer: str,
        retrieved_chunks: List[RetrievedChunk],
        retry_fn: Optional[Callable[[str], str]] = None,
    ) -> CitationCheckResult:
        if not self.cfg.enabled:
            return CitationCheckResult(is_valid=True, answer=answer, found_citations=[])

        valid_cids = {c.citation_id for c in retrieved_chunks}
        current_answer = answer
        retries = 0

        while True:
            found = self.extract_citations(current_answer)
            # Check if minimum number of citations met
            if len(found) >= self.cfg.min_citations_required:
                return CitationCheckResult(
                    is_valid=True,
                    answer=current_answer,
                    found_citations=found,
                    retries_used=retries,
                )

            # Check if we should retry
            if self.cfg.on_violation == "retry" and retry_fn and retries < self.cfg.max_retries:
                retries += 1
                current_answer = retry_fn(current_answer)
            else:
                return CitationCheckResult(
                    is_valid=False,
                    answer=current_answer,
                    found_citations=found,
                    retries_used=retries,
                    reason=f"Found {len(found)} citation(s), expected at least {self.cfg.min_citations_required}",
                )
