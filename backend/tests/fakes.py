"""Test doubles. ScriptedLLM plays back pre-written model turns, so agent tests are deterministic and
need no API key — while the agent loop, the tools and the database are all real."""

from collections.abc import Callable
from typing import Any

from app.agents.llm import LLMRefusalError, LLMTurn, ToolCall


def text_turn(text: str) -> LLMTurn:
    return LLMTurn(
        text=text,
        tool_calls=[],
        stop_reason="end_turn",
        assistant_content=[{"type": "text", "text": text}],
        usage={"input_tokens": 10, "output_tokens": 5},
    )


def tool_turn(*calls: tuple[str, dict[str, Any]]) -> LLMTurn:
    tool_calls = [ToolCall(id=f"toolu_{i}", name=name, arguments=args) for i, (name, args) in enumerate(calls)]
    content = [{"type": "tool_use", "id": c.id, "name": c.name, "input": c.arguments} for c in tool_calls]
    return LLMTurn(
        text="", tool_calls=tool_calls, stop_reason="tool_use", assistant_content=content, usage={"input_tokens": 10, "output_tokens": 5}
    )


class ScriptedLLM:
    """Returns the given turns in order. A turn may also be a function of the request (e.g. to echo
    tool results back), or the string "refuse" to simulate a refusal."""

    model = "scripted-test-llm"

    def __init__(self, *turns: LLMTurn | Callable[[dict[str, Any]], LLMTurn] | str) -> None:
        self.turns = list(turns)
        self.calls: list[dict[str, Any]] = []

    def generate(self, *, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> LLMTurn:
        request = {"system": system, "messages": [dict(m) for m in messages], "tools": tools}
        self.calls.append(request)
        if not self.turns:
            raise AssertionError("ScriptedLLM ran out of turns")
        turn = self.turns.pop(0)
        if turn == "refuse":
            raise LLMRefusalError("declined")
        if callable(turn):
            return turn(request)
        assert isinstance(turn, LLMTurn)
        return turn


def tool_results(request: dict[str, Any]) -> list[dict[str, Any]]:
    """The tool_result blocks of the last message the agent sent to the model."""
    content = request["messages"][-1]["content"]
    assert isinstance(content, list)
    return [block for block in content if block.get("type") == "tool_result"]
