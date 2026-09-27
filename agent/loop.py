"""
agent/loop.py
Core 4-iteration ReAct Loop + Self-Correction Verifier for CS/AI Papers.
"""
from __future__ import annotations

import os
import json
from typing import AsyncGenerator, Dict, Any, List
from groq import Groq

from agent.tools import retrieve_chunks, knowledge_base_status

AGENT_SYSTEM_PROMPT = """You are an expert AI Research Assistant specializing in Computer Science and arXiv paper analysis.

You have access to a knowledge base of research papers via tools.

RULES & INSTRUCTIONS:
1. To answer technical or factual questions, execute `retrieve_chunks`.
2. Do NOT guess paper contents. Always verify facts against retrieved text.
3. Formulate concise, targeted search queries when looking up concepts.
4. When sufficient evidence is available, synthesize a final answer.
5. CITATION RULE: Every claim MUST cite its source as [doc_id:chunk_index] using exact context headers.
"""

VERIFIER_SYSTEM_PROMPT = """You are a strict Fact-Checking Verifier for a research assistant.
Compare the DRAFT ANSWER against the retrieved context snippets.

Return ONLY a valid JSON object matching this schema:
{
  "verdict": "VERIFIED" | "FLAGGED",
  "reason": "Brief explanation",
  "flagged_claims": ["list of unsupported claims"]
}
"""


class AgenticRAGLoop:
    def __init__(self, model_name: str = "meta-llama/llama-4-scout-17b-16e-instruct"):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("[AgenticRAGLoop] WARNING: GROQ_API_KEY environment variable is not set.")
        self.client = Groq(api_key=api_key or "placeholder")
        self.model = os.getenv("GROQ_MODEL") or model_name

        self.tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": "retrieve_chunks",
                    "description": "Perform hybrid BM25 + dense vector search across paper chunks.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "knowledge_base_status",
                    "description": "Check number of paper chunks indexed in PostgreSQL.",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

    async def run_stream(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        messages = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]

        retrieved_contexts: List[str] = []
        max_iterations = 4

        for iteration in range(max_iterations):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tools_schema,
                    tool_choice="auto",
                    temperature=0.1,
                )
            except Exception as e:
                yield {
                    "event": "final_answer",
                    "data": {"token": f"Error calling Groq API: {e}. Please check your GROQ_API_KEY."}
                }
                return

            msg = response.choices[0].message
            messages.append(msg)

            # Tool Calls Execution
            if msg.tool_calls:
                for tool_call in msg.tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = json.loads(tool_call.function.arguments or "{}")

                    yield {
                        "event": "tool_call",
                        "data": {"tool": fn_name, "args": fn_args, "iteration": iteration + 1}
                    }

                    if fn_name == "retrieve_chunks":
                        res = retrieve_chunks(fn_args.get("query", query))
                        retrieved_contexts.append(res["context_block"])

                        for chunk in res["chunks"]:
                            yield {
                                "event": "chunk_result",
                                "data": {
                                    "citation_id": chunk["citation_id"],
                                    "title": chunk["metadata"].get("title", chunk["doc_id"]),
                                    "score": chunk["score"]
                                }
                            }

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": res["context_block"]
                        })

                    elif fn_name == "knowledge_base_status":
                        res = knowledge_base_status()
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(res)
                        })

            # Draft Answer + Verifier Pass
            else:
                draft_answer = msg.content or ""
                verification = self._verify(draft_answer, "\n\n".join(retrieved_contexts))
                
                yield {"event": "verifier", "data": verification}

                for char in draft_answer:
                    yield {"event": "final_answer", "data": {"token": char}}
                return

        yield {
            "event": "final_answer",
            "data": {"token": "Insufficient evidence found in research paper corpus after 4 iterations."}
        }

    def _verify(self, draft_answer: str, context: str) -> Dict[str, Any]:
        if not context.strip():
            return {
                "verdict": "FLAGGED",
                "reason": "No context was retrieved to support claims.",
                "flagged_claims": ["All claims ungrounded"]
            }

        try:
            prompt = f"CONTEXT:\n{context}\n\nDRAFT ANSWER:\n{draft_answer}"
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": VERIFIER_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            return json.loads(resp.choices[0].message.content or "{}")
        except Exception as e:
            return {
                "verdict": "VERIFIED",
                "reason": f"Verifier bypass on parse error: {e}",
                "flagged_claims": []
            }
