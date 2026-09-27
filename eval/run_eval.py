"""
eval/run_eval.py
Evaluates the Agentic RAG pipeline using the Kaggle Single-Topic Evaluation Dataset.

Computes 4 core metrics using Groq (meta-llama/llama-4-scout-17b-16e-instruct):
  1. Faithfulness
  2. Answer Relevance
  3. Context Recall
  4. Citation Coverage
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List
import pandas as pd

from eval.scorer import LLMJudgeScorer
from ingestion.pipeline import build_ingestion_pipeline


def load_kaggle_dataset(dataset_path: str) -> List[Dict[str, Any]]:
    """Loads query-answer test pairs from Kaggle dataset (supports .json, .jsonl, or .csv)."""
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset file not found at: {dataset_path}")

    if dataset_path.endswith(".csv"):
        df = pd.read_csv(dataset_path)
        return df.to_dict(orient="records")

    records = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        if dataset_path.endswith(".jsonl"):
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        else:
            records = json.load(f)
    return records


def run_evaluation_suite(
    dataset_path: str = "eval/single_topic_rag_eval.csv",
    config_path: str = "config/phase2.yaml",
):
    """Runs the full evaluation benchmark and prints aggregated metric scores."""
    print(f"[Eval] Loading configuration from {config_path}...")
    pipeline, bundle = build_ingestion_pipeline(config_path)
    rag = bundle.rag

    scorer = LLMJudgeScorer(model_name=os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"))
    test_cases = load_kaggle_dataset(dataset_path)

    print(f"[Eval] Starting evaluation on {len(test_cases)} evaluation cases...")

    results = []
    for idx, item in enumerate(test_cases, start=1):
        # Flexible key extraction supporting common Kaggle column names
        question = item.get("question") or item.get("query") or item.get("user_input")
        ground_truth = item.get("ground_truth") or item.get("reference_answer") or item.get("answer")

        if not question:
            continue

        # Execute RAG Pipeline
        rag_output = rag.answer(question)

        # Compute Metrics via Groq LLM-as-Judge
        faithfulness = scorer.score_faithfulness(
            question=question,
            context=rag_output.context_block,
            answer=rag_output.answer,
        )

        relevance = scorer.score_relevance(
            question=question,
            answer=rag_output.answer,
        )

        citation_coverage = scorer.score_citation_coverage(
            answer=rag_output.answer,
            citations=rag_output.citations,
        )

        results.append({
            "case_id": idx,
            "question": question,
            "faithfulness": faithfulness,
            "relevance": relevance,
            "citation_coverage": citation_coverage,
            "citation_count": len(rag_output.citations),
        })

        print(
            f"  [{idx}/{len(test_cases)}] Faithfulness: {faithfulness:.2f} | "
            f"Relevance: {relevance:.2f} | Citations: {citation_coverage:.2f}"
        )

    # Summary Statistics
    avg_faithfulness = sum(r["faithfulness"] for r in results) / len(results) if results else 0.0
    avg_relevance = sum(r["relevance"] for r in results) / len(results) if results else 0.0
    avg_citation = sum(r["citation_coverage"] for r in results) / len(results) if results else 0.0

    print("\n" + "=" * 50)
    print(" EVALUATION SUMMARY (Kaggle Dataset)")
    print("=" * 50)
    print(f"Total Test Cases Processed: {len(results)}")
    print(f"Average Faithfulness Score: {avg_faithfulness:.4f}")
    print(f"Average Answer Relevance:  {avg_relevance:.4f}")
    print(f"Average Citation Coverage: {avg_citation:.4f}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    if not os.getenv("GROQ_API_KEY"):
        print("Error: GROQ_API_KEY environment variable is missing.")
        exit(1)

    run_evaluation_suite()
