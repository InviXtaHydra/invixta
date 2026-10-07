"""OllamaClient against a small fake Ollama server: real HTTP and real line-by-line streaming, so the
translation to and from Ollama's API is tested without downloading a model."""

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

from app.agents.ollama_client import OllamaClient, to_ollama_messages, to_ollama_tools
from app.core.exceptions import ServiceUnavailableError
from app.tools.support_tools import TOOL_DEFINITIONS


class FakeOllama:
    """Replies to POST /api/chat with the scripted lines and records the requests it received."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.lines: list[dict[str, Any]] = []
        self.status = 200
        self.models = [{"name": "qwen3:8b", "model": "qwen3:8b"}]


@pytest.fixture
def ollama() -> Iterator[tuple[FakeOllama, str]]:
    fake = FakeOllama()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            fake.requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            if fake.status != 200:
                self.send_response(fake.status)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "model 'qwen3:8b' not found"}).encode())
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.end_headers()
            for line in fake.lines:
                self.wfile.write(json.dumps(line).encode() + b"\n")
                self.wfile.flush()

        def do_GET(self) -> None:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"models": fake.models}).encode())

        def log_message(self, *args: Any) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield fake, f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def client(url: str) -> OllamaClient:
    return OllamaClient(url=url, model="qwen3:8b", timeout_seconds=5)


def test_streams_text_and_reports_usage(ollama: tuple[FakeOllama, str]) -> None:
    fake, url = ollama
    fake.lines = [
        {"message": {"role": "assistant", "content": "Your order "}, "done": False},
        {"message": {"role": "assistant", "content": "has shipped."}, "done": False},
        {"message": {"role": "assistant", "content": ""}, "done": True, "done_reason": "stop", "prompt_eval_count": 812, "eval_count": 9},
    ]
    pieces: list[str] = []
    turn = client(url).generate(system="Be brief.", messages=[{"role": "user", "content": "Where is it?"}], on_text=pieces.append)

    assert pieces == ["Your order ", "has shipped."]
    assert turn.text == "Your order has shipped."
    assert turn.tool_calls == [] and turn.stop_reason == "stop"
    assert turn.usage == {"input_tokens": 812, "output_tokens": 9}

    sent = fake.requests[0]
    assert sent["model"] == "qwen3:8b" and sent["stream"] is True and sent["think"] is False
    assert sent["options"]["num_ctx"] == 8192  # big enough for prompt + tools + sources
    assert sent["messages"] == [{"role": "system", "content": "Be brief."}, {"role": "user", "content": "Where is it?"}]
    assert "tools" not in sent


def test_parses_tool_calls_with_object_or_string_arguments(ollama: tuple[FakeOllama, str]) -> None:
    fake, url = ollama
    fake.lines = [
        {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "get_order_status", "arguments": {"order_id": "10014"}}},
                    {"function": {"name": "search_knowledge_base", "arguments": '{"query": "return policy"}'}},
                ],
            },
            "done": False,
        },
        {"done": True, "done_reason": "stop"},
    ]
    turn = client(url).generate(system="s", messages=[{"role": "user", "content": "q"}], tools=TOOL_DEFINITIONS)

    assert [(c.name, c.arguments) for c in turn.tool_calls] == [
        ("get_order_status", {"order_id": "10014"}),
        ("search_knowledge_base", {"query": "return policy"}),
    ]
    assert turn.stop_reason == "tool_use"
    assert [b["type"] for b in turn.assistant_content] == ["tool_use", "tool_use"]
    tools = fake.requests[0]["tools"]
    assert tools[0]["type"] == "function" and tools[0]["function"]["name"] == "get_order_status"
    assert tools[0]["function"]["parameters"]["required"] == ["order_id"]


def test_tool_rounds_are_translated_to_ollama_messages() -> None:
    history: list[dict[str, Any]] = [
        {"role": "user", "content": "Where is order 10014?"},
        {
            "role": "assistant",
            "content": [{"type": "tool_use", "id": "call_1", "name": "get_order_status", "input": {"order_id": "10014"}}],
        },
        {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "call_1", "content": '{"status": "shipped"}', "is_error": False}],
        },
    ]
    assert to_ollama_messages("system prompt", history) == [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "Where is order 10014?"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": "get_order_status", "arguments": {"order_id": "10014"}}}],
        },
        {"role": "tool", "tool_name": "get_order_status", "content": '{"status": "shipped"}'},
    ]
    assert to_ollama_tools(TOOL_DEFINITIONS[:1])[0]["function"]["description"].startswith("Look up one order")


def test_missing_model_gives_a_clear_instruction(ollama: tuple[FakeOllama, str]) -> None:
    fake, url = ollama
    fake.status = 404
    with pytest.raises(ServiceUnavailableError, match="ollama pull qwen3:8b"):
        client(url).generate(system="s", messages=[{"role": "user", "content": "q"}])


def test_ollama_not_running_gives_a_clear_instruction() -> None:
    with pytest.raises(ServiceUnavailableError, match="ollama serve"):
        client("http://127.0.0.1:9").generate(system="s", messages=[{"role": "user", "content": "q"}])


def test_status_reports_ok_missing_model_or_unreachable(ollama: tuple[FakeOllama, str]) -> None:
    fake, url = ollama
    assert client(url).status() == "ok"
    fake.models = [{"name": "llama3.1:8b", "model": "llama3.1:8b"}]
    assert client(url).status() == "model_missing"
    assert client("http://127.0.0.1:9").status() == "unreachable"
