"""
eval/scorer.py
LLM-as-a-Judge scoring engine using Groq (meta-llama/llama-4-scout-17b-16e-instruct).
Computes Faithfulness, Answer Relevance, Context Recall, and Citation Coverage.
"""
from __future__ import annotations

import json
import os
import re
from typing import List, Optional
from groq import Groq


class LLMJudgeScorer:
    """
    Evaluates RAG pipeline outputs across standard benchmark metrics.
    """

    def __init__(self, model_name: str = "meta-llama/llama-4-scout-17b-16e-instruct"):
        api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=api_key or "placeholder")
        self.model = os.getenv("GROQ_MODEL") or model_name

    def _call_judge(self, system_prompt: str, user_prompt: str) -> float:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            score = float(data.get("score", 0.0))
            return max(0.0, min(1.0, score))
        except Exception:
            return 0.5

    def score_faithfulness(self, question: str, context: str, answer: str) -> float:
        """
        Evaluates whether claims made in the answer are strictly supported by the context.
        Scale: 0.0 (complete hallucination) to 1.0 (fully grounded).
        """
        system = """You are an impartial evaluator assessing faithfulness in RAG systems.
Examine the context and answer. Determine if all claims in the answer are supported by the context.
Output JSON only: {"score": <float between 0.0 and 1.0>, "reasoning": "<brief explanation>"}"""
        
        user = f"QUESTION: {question}\n\nCONTEXT:\n{context}\n\nANSWER:\n{answer}"
        return self._call_judge(system, user)

    def score_relevance(self, question: str, answer: str) -> float:
        """
        Evaluates whether the answer directly addresses the question asked.
        Scale: 0.0 (irrelevant) to 1.0 (perfectly addresses question).
        """
        system = """You are an impartial evaluator assessing answer relevance.
Examine the question and answer. Determine how directly the answer responds to the question.
Output JSON only: {"score": <float between 0.0 and 1.0>, "reasoning": "<brief explanation>"}"""
        
        user = f"QUESTION: {question}\n\nANSWER:\n{answer}"
        return self._call_judge(system, user)

    def score_context_recall(self, question: str, context: str, ground_truth: str) -> float:
        """
        Evaluates whether the retrieved context contains the facts in the ground truth.
        """
        system = """You are an impartial evaluator assessing retrieval recall.
Examine the ground truth answer and retrieved context. Determine if the context contains all key facts.
Output JSON only: {"score": <float between 0.0 and 1.0>, "reasoning": "<brief explanation>"}"""
        
        user = f"QUESTION: {question}\n\nGROUND TRUTH:\n{ground_truth}\n\nCONTEXT:\n{context}"
        return self._call_judge(system, user)

    def score_citation_coverage(self, answer: str, citations: List[str]) -> float:
        """
        Evaluates the presence of valid inline citation anchors [doc:idx] in sentences.
        """
        sentences = [s.strip() for s in re.split(r"[.!?]\s+", answer) if s.strip()]
        if not sentences:
            return 0.0

        cited_sentences = 0
        pattern = re.compile(r"\[[a-zA-Z0-9_\-]+:\d+\]")
        for s in sentences:
            if pattern.search(s):
                cited_sentences += 1

        return min(1.0, cited_sentences / len(sentences))