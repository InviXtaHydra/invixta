"""LLM abstraction. The rest of the app talks to `LLMClient`, never to a model server directly, so the
model can be swapped (or faked in tests) without touching the agent or RAG code.

The app's own message format (each client translates it to what its model server expects):

    {"role": "user" | "assistant", "content": "plain text"}
    {"role": "assistant", "content": [{"type": "text", "text": ...},
                                      {"type": "tool_use", "id": ..., "name": ..., "input": {...}}]}
    {"role": "user", "content": [{"type": "tool_result", "tool_use_id": ..., "content": "json", "is_error": bool}]}

Tools are described as {"name": ..., "description": ..., "input_schema": {JSON Schema}}.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Protocol

from app.core.config import get_settings

if TYPE_CHECKING:
    from app.agents.ollama_client import OllamaClient


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMTurn:
    """One model response: final text and/or tool calls the model wants us to run."""

    text: str
    tool_calls: list[ToolCall]
    stop_reason: str
    # This turn in the app's message format; the agent appends it to the history for the next request.
    assistant_content: list[dict[str, Any]]
    usage: dict[str, int] = field(default_factory=dict)


TextCallback = Callable[[str], None]


class LLMClient(Protocol):
    model: str

    def generate(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        on_text: TextCallback | None = None,
    ) -> LLMTurn:
        """One model turn. If on_text is given, it's called with each piece of text as it's generated.

        Raises ServiceUnavailableError when the model server can't be reached or fails."""
        ...


class LLMRefusalError(Exception):
    """The model declined to answer. The agent then replies with a polite fallback message."""


@lru_cache
def _ollama_client(
    url: str, model: str, temperature: float, context_tokens: int, max_tokens: int, think: bool, timeout: int
) -> "OllamaClient":
    """One client per configuration (lru_cache), created on first use."""
    from app.agents.ollama_client import OllamaClient

    return OllamaClient(
        url=url,
        model=model,
        temperature=temperature,
        context_tokens=context_tokens,
        max_tokens=max_tokens,
        think=think,
        timeout_seconds=timeout,
    )


def get_llm() -> LLMClient:
    """FastAPI dependency: the configured model.

    LLM_PROVIDER=ollama (default): a local model served by Ollama, free and private.
    LLM_PROVIDER=scripted: the deterministic stand-in used by the end-to-end tests in CI."""
    settings = get_settings()
    if settings.llm_provider == "scripted":
        from app.agents.scripted_llm import ScriptedSupportLLM

        return ScriptedSupportLLM()
    return _ollama_client(
        settings.ollama_url.rstrip("/"),
        settings.llm_model,
        settings.llm_temperature,
        settings.llm_context_tokens,
        settings.llm_max_tokens,
        settings.llm_think,
        settings.llm_timeout_seconds,
    )
