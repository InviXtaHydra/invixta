"""A deterministic, rule-based stand-in for the LLM — for end-to-end tests only.

The browser end-to-end tests (frontend/e2e) must be repeatable and must run in CI, where there is no
GPU or 5 GB model to run Ollama with. With LLM_PROVIDER=scripted the backend uses this class instead of Ollama. Everything else
stays real: the agent loop, the tools, the database queries, the vector search and the streaming.
Only the "thinking" is replaced by simple rules:

    "cancel" + an order number     → request_order_cancellation
    "in stock" / "available"       → search_products
    message with an order number   → get_order_status
    "ticket"                       → get_support_tickets
    "order" / "parcel" (no number) → get_customer_orders
    anything else                  → search_knowledge_base

and the answer is written from the tool result. It is not an AI and is refused in production
(see Settings.no_test_llm_in_production).
"""

import json
import re
import time
from typing import Any

from app.agents.llm import LLMTurn, TextCallback, ToolCall
from app.rag.rag_service import NOT_FOUND_MESSAGE

ORDER_NUMBER = re.compile(r"#?\b(\d{5,9})\b")
DAMAGE_WORDS = ("damaged", "broken", "beschadigd", "kapot")


class ScriptedSupportLLM:
    model = "scripted-e2e"

    def __init__(self, delay_seconds: float = 0.02) -> None:
        self.delay = delay_seconds  # pause between streamed words, so streaming is visible in the UI

    def generate(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        on_text: TextCallback | None = None,
    ) -> LLMTurn:
        last = messages[-1]
        if isinstance(last["content"], list):  # the results of the tools we asked for
            return self._answer(self._answer_from_tools(messages), on_text)
        text = str(last["content"])
        if tools is None:
            return self._answer("Could you tell me a bit more about what you need?", on_text)
        call = self._choose_tool(text)
        if call is None:
            return self._answer("I'm sorry to hear that. What is the order number, so I can look into it?", on_text)
        return LLMTurn(
            text="",
            tool_calls=[call],
            stop_reason="tool_use",
            assistant_content=[{"type": "tool_use", "id": call.id, "name": call.name, "input": call.arguments}],
        )

    # --- Rules ----------------------------------------------------------------------------------

    def _choose_tool(self, text: str) -> ToolCall | None:
        lower = text.lower()
        number = ORDER_NUMBER.search(text)
        damaged = any(word in lower for word in DAMAGE_WORDS)
        if damaged and number:
            args = {
                "subject": f"Order #{number.group(1)} arrived damaged",
                "description": text,
                "priority": "high",
                "order_id": number.group(1),
            }
            return ToolCall(id="scripted_1", name="create_support_ticket", arguments=args)
        if damaged:
            return None  # ask for the order number first
        if number and any(w in lower for w in ("cancel", "annuleer", "annuleren")):
            return ToolCall(id="scripted_1", name="request_order_cancellation", arguments={"order_id": number.group(1)})
        if any(w in lower for w in ("in stock", "available", "op voorraad", "do you have")):
            return ToolCall(id="scripted_1", name="search_products", arguments={"query": _product_words(text)})
        if number:
            return ToolCall(id="scripted_1", name="get_order_status", arguments={"order_id": number.group(1)})
        if "ticket" in lower:
            return ToolCall(id="scripted_1", name="get_support_tickets", arguments={})
        if any(word in lower for word in ("my order", "my orders", "parcel", "package", "bestelling")):
            return ToolCall(id="scripted_1", name="get_customer_orders", arguments={})
        return ToolCall(id="scripted_1", name="search_knowledge_base", arguments={"query": text[:500]})

    def _answer_from_tools(self, messages: list[dict[str, Any]]) -> str:
        requested = {block["id"]: block["name"] for block in messages[-2]["content"] if block.get("type") == "tool_use"}
        block = messages[-1]["content"][0]
        name = requested.get(block["tool_use_id"], "")
        data = json.loads(block["content"])
        if block.get("is_error"):
            return f"I couldn't do that on your account: {data.get('error', 'unknown error')}"
        if name == "get_order_status":
            parts = [f"Order #{data['order_id']} is currently {data['status']}."]
            if data.get("carrier") and data.get("tracking_number"):
                parts.append(f"It's with {data['carrier']}, tracking number {data['tracking_number']}.")
            if data.get("estimated_delivery") and data["status"] not in ("delivered", "cancelled"):
                parts.append(f"Estimated delivery: {data['estimated_delivery']}.")
            return " ".join(parts)
        if name == "get_customer_orders":
            if not data["orders"]:
                return "I don't see any orders on your account."
            latest = data["orders"][0]
            return (
                f"You have {data['total']} orders. The most recent one is #{latest['order_id']}, "
                f"ordered on {latest['ordered_on']}, and it is {latest['status']}."
            )
        if name == "get_support_tickets":
            if not data["tickets"]:
                return "You don't have any support tickets."
            open_ones = [t for t in data["tickets"] if t["status"] in ("open", "in_progress")]
            latest_id = data["tickets"][0]["ticket_id"]
            return f"You have {data['total']} tickets, {len(open_ones)} of them still open. The latest is #{latest_id}."
        if name == "request_order_cancellation":
            return f"Order #{data['order_id']} can still be cancelled. Confirm it with the button below; until then nothing changes."
        if name == "search_products":
            if not data["results"]:
                return "I couldn't find that product in the shop."
            first = data["results"][0]
            sizes = ", ".join(first["sizes_in_stock"]) or "no sizes"
            return f"The {first['product']} costs EUR {first['price_eur']} and is in stock in: {sizes}."
        if name == "create_support_ticket":
            return f"I've opened ticket #{data['ticket_id']} with {data['priority']} priority. A colleague will get back to you."
        if name == "search_knowledge_base":
            if not data["results"]:
                return NOT_FOUND_MESSAGE
            # The two best passages, cited like the real model would.
            top = data["results"][:2]
            passages = " ".join(f"{r['text']} [{r['source']}]" for r in top)
            documents = " and ".join(sorted({r["document"] for r in top}))
            return f"Here is what I found in {documents}: {passages}"
        return "Done."

    def _answer(self, text: str, on_text: TextCallback | None) -> LLMTurn:
        if on_text is not None:
            for i, word in enumerate(text.split(" ")):
                on_text(word if i == 0 else f" {word}")
                time.sleep(self.delay)
        return LLMTurn(text=text, tool_calls=[], stop_reason="end_turn", assistant_content=[{"type": "text", "text": text}])


def _product_words(text: str) -> str:
    """'Is the Polder United home shirt in stock?' → 'Polder United home' (the words that name the product)."""
    stop = {"is", "the", "in", "stock", "available", "do", "you", "have", "a", "an", "shirt", "?", "still"}
    words = [w.strip("?.,!") for w in text.split()]
    return " ".join(w for w in words if w and w.lower() not in stop)[:100] or text[:100]
