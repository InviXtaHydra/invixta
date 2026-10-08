"""A local language model served by Ollama (https://ollama.com): free, no API key, nothing leaves the machine.

Ollama runs next to the app and has an HTTP API. We use one endpoint, POST /api/chat:

    request:  {"model": "qwen3:8b", "messages": [...], "tools": [...], "stream": true}
    response: one JSON object per line while the model writes, e.g.
              {"message": {"content": "Your order "}, "done": false}
              {"message": {"tool_calls": [{"function": {"name": "get_order_status", "arguments": {...}}}]}, "done": false}
              {"done": true, "prompt_eval_count": 812, "eval_count": 64}

This class translates the app's message format (see llm.py) to Ollama's and back, so the agent,
tools and RAG code don't know which model they talk to. It only uses the standard library (urllib).
"""

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from app.agents.llm import LLMTurn, TextCallback, ToolCall
from app.core.exceptions import ServiceUnavailableError

logger = logging.getLogger("invixta.llm")


def to_ollama_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """{"name", "description", "input_schema"} → Ollama's (OpenAI-style) function definitions."""
    return [
        {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}
        for t in tools
    ]


def to_ollama_messages(system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The app's message format → Ollama's chat messages.

    - an assistant turn with tool_use blocks → {"role": "assistant", "content": text, "tool_calls": [...]}
    - a user message with tool_result blocks → one {"role": "tool", "tool_name": ..., "content": ...} per result
    """
    result: list[dict[str, Any]] = [{"role": "system", "content": system}]
    tool_names: dict[str, str] = {}  # tool_use id → tool name, needed for the tool messages
    for message in messages:
        content = message["content"]
        if isinstance(content, str):
            result.append({"role": message["role"], "content": content})
            continue
        if message["role"] == "assistant":
            text = "".join(block["text"] for block in content if block["type"] == "text")
            calls = []
            for block in content:
                if block["type"] == "tool_use":
                    tool_names[block["id"]] = block["name"]
                    calls.append({"function": {"name": block["name"], "arguments": block["input"]}})
            result.append({"role": "assistant", "content": text, "tool_calls": calls} if calls else {"role": "assistant", "content": text})
        else:
            for block in content:
                if block["type"] == "tool_result":
                    result.append({"role": "tool", "tool_name": tool_names.get(block["tool_use_id"], ""), "content": block["content"]})
                elif block["type"] == "text":
                    result.append({"role": "user", "content": block["text"]})
    return result


def _arguments(value: Any) -> dict[str, Any]:
    """Tool arguments arrive as a JSON object; some models send a JSON string instead."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


class OllamaClient:
    def __init__(
        self,
        *,
        url: str,
        model: str,
        temperature: float = 0.2,
        context_tokens: int = 8192,
        max_tokens: int = 1024,
        think: bool = False,
        timeout_seconds: int = 300,
    ) -> None:
        self.url = url
        self.model = model
        self.temperature = temperature  # low: factual support answers, not creative writing
        self.context_tokens = context_tokens  # Ollama's default window is too small for prompt + tools + sources
        self.max_tokens = max_tokens
        self.think = think  # qwen3's "thinking" mode: better reasoning, much slower on a laptop
        self.timeout = timeout_seconds

    def generate(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        on_text: TextCallback | None = None,
    ) -> LLMTurn:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": to_ollama_messages(system, messages),
            "stream": True,
            "think": self.think,
            "keep_alive": "30m",  # keep the model in memory between questions
            "options": {"temperature": self.temperature, "num_ctx": self.context_tokens, "num_predict": self.max_tokens},
        }
        if tools:
            payload["tools"] = to_ollama_tools(tools)

        started = time.perf_counter()
        text_parts: list[str] = []
        calls: list[ToolCall] = []
        final: dict[str, Any] = {}
        try:
            with self._post("/api/chat", payload) as response:
                for line in response:  # one JSON object per line
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    if "error" in chunk:
                        raise ServiceUnavailableError(f"The AI model failed: {chunk['error']}")
                    message = chunk.get("message") or {}
                    piece = message.get("content") or ""
                    if piece:
                        text_parts.append(piece)
                        if on_text is not None:
                            on_text(piece)
                    for call in message.get("tool_calls") or []:
                        function = call.get("function") or {}
                        calls.append(
                            ToolCall(
                                id=str(call.get("id") or f"call_{len(calls) + 1}"),
                                name=str(function.get("name", "")),
                                arguments=_arguments(function.get("arguments")),
                            )
                        )
                    if chunk.get("done"):
                        final = chunk
        except urllib.error.HTTPError as exc:
            raise self._http_error(exc) from exc
        except TimeoutError as exc:
            logger.error("llm request failed", extra={"error": "timeout", "model": self.model})
            raise ServiceUnavailableError("The AI model took too long to answer. Please try again.") from exc
        except urllib.error.URLError as exc:
            logger.error("llm request failed", extra={"error": "unreachable", "model": self.model})
            raise ServiceUnavailableError(f"Can't reach Ollama at {self.url}. Is it running? Start it with: ollama serve") from exc

        usage = {"input_tokens": int(final.get("prompt_eval_count", 0)), "output_tokens": int(final.get("eval_count", 0))}
        stop_reason = "tool_use" if calls else str(final.get("done_reason", "stop"))
        logger.info(
            "llm request",
            extra={
                "model": self.model,
                "stop_reason": stop_reason,
                "duration_ms": round((time.perf_counter() - started) * 1000),
                "tools_offered": len(tools or []),
                **usage,
            },
        )
        text = "".join(text_parts).strip()
        content: list[dict[str, Any]] = [{"type": "text", "text": text}] if text else []
        content += [{"type": "tool_use", "id": c.id, "name": c.name, "input": c.arguments} for c in calls]
        return LLMTurn(text=text, tool_calls=calls, stop_reason=stop_reason, assistant_content=content, usage=usage)

    def status(self) -> str:
        """For /health: "ok", "model_missing" (run `ollama pull <model>`) or "unreachable"."""
        try:
            with self._get("/api/tags", timeout=2) as response:
                models = json.loads(response.read()).get("models", [])
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return "unreachable"
        names = {m.get("name", "") for m in models} | {m.get("model", "") for m in models}
        wanted = self.model if ":" in self.model else f"{self.model}:latest"
        return "ok" if wanted in names else "model_missing"

    # --- HTTP helpers -----------------------------------------------------------------------------

    def _post(self, path: str, payload: dict[str, Any]) -> Any:
        request = urllib.request.Request(
            f"{self.url}{path}", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST"
        )
        return urllib.request.urlopen(request, timeout=self.timeout)

    def _get(self, path: str, timeout: float) -> Any:
        return urllib.request.urlopen(f"{self.url}{path}", timeout=timeout)

    def _http_error(self, exc: urllib.error.HTTPError) -> ServiceUnavailableError:
        try:
            detail = str(json.loads(exc.read()).get("error", ""))
        except (json.JSONDecodeError, ValueError):
            detail = ""
        logger.error("llm request failed", extra={"error": f"http_{exc.code}", "model": self.model})
        if exc.code == 404 and "not found" in detail:
            return ServiceUnavailableError(f"The AI model '{self.model}' isn't downloaded yet. Run: ollama pull {self.model}")
        return ServiceUnavailableError(f"The AI model failed ({exc.code}): {detail or 'unknown error'}")
