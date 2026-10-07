"""Query rewriting: turn a customer's message into a short English search query before searching.

Why: the embedding model (bge-small-en) is very good at English but matches Dutch or French questions
poorly ("Wat is jullie retourbeleid?" scored 0.41, below the 0.6 threshold). A short call to the local
LLM translates and condenses the message, using the conversation for context, so a follow-up such as
"and for Belgium?" becomes "delivery time to Belgium".

Measured on the evaluation set (scripts/evaluate_rag.py): Dutch hit@1 went from 0.11 to 0.89.
"""

import logging
import time
from typing import Any

from app.agents.llm import LLMClient

logger = logging.getLogger("supportai.rag")

SEARCH_QUERY_PROMPT = """You turn a customer's message into one short ENGLISH search query for the policy documents of a
web shop (returns, refunds, shipping, delivery, warranty, payments, products).
- Always write English, also when the customer writes Dutch, French or another language (translate).
- Keep the customer's own key words; use the conversation only to understand what "it" or "that" refers to.
- Reply with the query only: no quotes, no explanation."""


def transcript(history: list[dict[str, Any]], message: str, last_turns: int = 4) -> str:
    """The last few plain-text turns plus the new message, as one block of text for the model."""
    lines = []
    for turn in history[-last_turns:]:
        if isinstance(turn.get("content"), str):
            who = "Customer" if turn["role"] == "user" else "Assistant"
            lines.append(f"{who}: {turn['content'][:500]}")
    lines.append(f"Customer (last message): {message}")
    return "\n".join(lines)


def rewrite_search_query(llm: LLMClient, message: str, history: list[dict[str, Any]] | None = None) -> str:
    started = time.perf_counter()
    turn = llm.generate(system=SEARCH_QUERY_PROMPT, messages=[{"role": "user", "content": transcript(history or [], message)}])
    query = turn.text.strip().strip("\"'").splitlines()[0].strip() if turn.text.strip() else ""
    if not 3 <= len(query) <= 300:  # empty or rambling: fall back to the message itself
        query = message[:300]
    logger.info("search query rewritten", extra={"duration_ms": round((time.perf_counter() - started) * 1000), "query_chars": len(query)})
    return query
