"""POST /chat/stream: Server-Sent Events from the real agent, tools and database (scripted LLM)."""

import json
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.llm import get_llm
from app.core.exceptions import ServiceUnavailableError
from app.main import app
from app.models import Message, User, UserRole
from tests.conftest import auth_header, make_order, make_staff
from tests.fakes import ScriptedLLM, text_turn, tool_turn


def read_events(response: Any) -> list[dict[str, Any]]:
    assert response.headers["content-type"].startswith("text/event-stream")
    events = []
    for block in response.text.split("\n\n"):
        if block.startswith("data: "):
            events.append(json.loads(block.removeprefix("data: ")))
    return events


def use(llm: ScriptedLLM) -> None:
    app.dependency_overrides[get_llm] = lambda: llm


def test_stream_reports_tools_then_text_then_done(client: TestClient, db: Session, alice: User) -> None:
    order = make_order(db, alice.customer)  # type: ignore[arg-type]
    use(ScriptedLLM(tool_turn(("get_order_status", {"order_id": str(order.id)})), text_turn(f"Order #{order.id} has shipped.")))

    response = client.post("/chat/stream", json={"message": f"Where is order {order.id}?"}, headers=auth_header(alice))
    assert response.status_code == 200
    events = read_events(response)
    types = [e["type"] for e in events]

    assert types[0] == "start" and types[-1] == "done"
    assert types.index("tool_start") < types.index("tool_end") < types.index("text")
    tool_end = next(e for e in events if e["type"] == "tool_end")
    assert tool_end["name"] == "get_order_status" and tool_end["summary"] == f"Order #{order.id}: shipped"
    assert "".join(e["delta"] for e in events if e["type"] == "text") == f"Order #{order.id} has shipped."

    done = events[-1]
    assert done["conversation_id"] == events[0]["conversation_id"]
    assert done["message"] == f"Order #{order.id} has shipped."
    assert done["tool_calls"][0]["status"] == "ok"
    stored = db.scalars(select(Message).where(Message.conversation_id == done["conversation_id"])).all()
    assert len(stored) == 2


def test_text_before_a_tool_call_is_kept_in_the_answer(client: TestClient, db: Session, alice: User) -> None:
    order = make_order(db, alice.customer)  # type: ignore[arg-type]
    use(ScriptedLLM(tool_turn(("get_order_status", {"order_id": str(order.id)}), text="Let me check."), text_turn("It has shipped.")))
    events = read_events(client.post("/chat/stream", json={"message": f"Order {order.id}?"}, headers=auth_header(alice)))
    streamed = "".join(e["delta"] for e in events if e["type"] == "text")
    assert streamed == "Let me check.\n\nIt has shipped."
    assert events[-1]["message"] == streamed  # what was streamed is what's stored


def test_llm_failure_mid_stream_sends_an_error_event_and_stores_nothing(client: TestClient, db: Session, alice: User) -> None:
    use(ScriptedLLM(ServiceUnavailableError("The AI assistant is temporarily unavailable. Please try again.")))
    events = read_events(client.post("/chat/stream", json={"message": "Hello"}, headers=auth_header(alice)))
    assert [e["type"] for e in events] == ["start", "error"]
    assert "temporarily unavailable" in events[1]["detail"]
    assert db.scalars(select(Message)).first() is None


def test_access_errors_happen_before_streaming(client: TestClient, db: Session, alice: User, bob: User) -> None:
    use(ScriptedLLM(text_turn("Hi Bob.")))
    bobs = read_events(client.post("/chat/stream", json={"message": "Hi"}, headers=auth_header(bob)))[-1]["conversation_id"]

    use(ScriptedLLM())
    assert client.post("/chat/stream", json={"conversation_id": bobs, "message": "Hi"}, headers=auth_header(alice)).status_code == 404
    staff = make_staff(db, "agent@example.com", UserRole.AGENT)
    assert client.post("/chat/stream", json={"message": "Hi"}, headers=auth_header(staff)).status_code == 403


def test_stream_when_ollama_is_down_ends_with_a_helpful_error(client: TestClient, db: Session, alice: User) -> None:
    events = read_events(client.post("/chat/stream", json={"message": "Hi"}, headers=auth_header(alice)))
    assert [e["type"] for e in events] == ["start", "error"]
    assert "ollama serve" in events[1]["detail"]
    assert db.scalars(select(Message)).first() is None


def test_chat_messages_are_rate_limited(client: TestClient, alice: User) -> None:
    from app.core.rate_limit import chat_limiter

    limiter = chat_limiter()
    original = limiter.limit
    limiter.limit = 2
    try:
        use(ScriptedLLM(text_turn("One."), text_turn("Two.")))
        headers = auth_header(alice)
        assert client.post("/chat", json={"message": "1"}, headers=headers).status_code == 200
        assert client.post("/chat", json={"message": "2"}, headers=headers).status_code == 200
        third = client.post("/chat", json={"message": "3"}, headers=headers)
        assert third.status_code == 429
        assert int(third.headers["Retry-After"]) >= 1
    finally:
        limiter.limit = original
