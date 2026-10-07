"""LLM abstraction. The rest of the app talks to `LLMClient`, never to a vendor SDK directly, so the
provider can be swapped (or faked in tests) without touching the agent or RAG code.

Messages use the widely used Messages-API shape:
    {"role": "user" | "assistant", "content": str | list[content blocks]}
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast

from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError

if TYPE_CHECKING:
    from anthropic.types.beta import BetaMessageParam, BetaToolParam

logger = logging.getLogger("supportai.llm")

Effort = Literal["low", "medium", "high", "xhigh", "max"]


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
    # The provider's own content blocks, appended to the history as-is for the next request.
    assistant_content: Any
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
        """One model turn. If on_text is given, it's called with each piece of text as it's generated."""
        ...


class LLMRefusalError(Exception):
    """The model declined the request (safety classifiers)."""


class AnthropicClient:
    """Claude via the official Anthropic SDK.

    - `fallbacks="default"`: if the model declines a request, the API retries it on a suitable
      fallback model server-side instead of returning a refusal.
    - `effort` trades answer depth against latency/cost; support answers do well at medium.
    - Responses are always streamed: text reaches the user while it's generated, and long answers
      don't run into request timeouts. `get_final_message()` gives the complete response afterwards.
    """

    def __init__(self, api_key: str, model: str, effort: str, max_tokens: int) -> None:
        import anthropic

        self._anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=api_key, max_retries=2, timeout=90.0)
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens

    def generate(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        on_text: TextCallback | None = None,
    ) -> LLMTurn:
        anthropic = self._anthropic
        started = time.perf_counter()
        try:
            with self.client.beta.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                messages=cast("list[BetaMessageParam]", messages),
                tools=cast("list[BetaToolParam]", tools or []),
                output_config={"effort": cast(Effort, self.effort)},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            ) as stream:
                for piece in stream.text_stream:
                    if on_text is not None:
                        on_text(piece)
                response = stream.get_final_message()
        except anthropic.AuthenticationError as exc:
            logger.error("llm request failed", extra={"error": "authentication", "model": self.model})
            raise ServiceUnavailableError("The AI assistant is misconfigured (invalid API key)") from exc
        except anthropic.RateLimitError as exc:
            logger.warning("llm request failed", extra={"error": "rate_limited", "model": self.model})
            raise ServiceUnavailableError("The AI assistant is busy right now. Please try again in a moment.") from exc
        except (anthropic.APIConnectionError, anthropic.APIStatusError) as exc:
            logger.error("llm request failed", extra={"error": type(exc).__name__, "model": self.model})
            raise ServiceUnavailableError("The AI assistant is temporarily unavailable. Please try again.") from exc

        usage = {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
        logger.info(
            "llm request",
            extra={
                "model": response.model,
                "stop_reason": response.stop_reason,
                "duration_ms": round((time.perf_counter() - started) * 1000),
                "tools_offered": len(tools or []),
                **usage,
            },
        )
        if response.stop_reason == "refusal":
            raise LLMRefusalError("The request was declined")

        text = "".join(block.text for block in response.content if block.type == "text").strip()
        calls = [ToolCall(id=b.id, name=b.name, arguments=dict(b.input)) for b in response.content if b.type == "tool_use"]
        return LLMTurn(text=text, tool_calls=calls, stop_reason=response.stop_reason or "", assistant_content=response.content, usage=usage)


@lru_cache
def _anthropic_client(api_key: str, model: str, effort: str, max_tokens: int) -> AnthropicClient:
    return AnthropicClient(api_key, model, effort, max_tokens)


def get_llm() -> LLMClient | None:
    """FastAPI dependency: the configured LLM, or None when no API key is set.

    Endpoints call require_llm() after request validation, so bad input still gets a 422.
    LLM_PROVIDER=scripted selects the deterministic stand-in used by the end-to-end tests."""
    settings = get_settings()
    if settings.llm_provider == "scripted":
        from app.agents.scripted_llm import ScriptedSupportLLM

        return ScriptedSupportLLM()
    if not settings.anthropic_api_key:
        return None
    return _anthropic_client(settings.anthropic_api_key, settings.llm_model, settings.llm_effort, settings.llm_max_tokens)


def require_llm(llm: LLMClient | None) -> LLMClient:
    if llm is None:
        raise ServiceUnavailableError("The AI assistant isn't configured: set ANTHROPIC_API_KEY in .env")
    return llm
