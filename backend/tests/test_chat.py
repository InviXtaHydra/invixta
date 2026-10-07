"""POST /chat end to end: real auth, database, tools and embeddings, with a scripted LLM."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.llm import get_llm
from app.main import app
from app.models import Message, MessageRole, User, UserRole
from tests.conftest import auth_header, make_order, make_staff
from tests.fakes import ScriptedLLM, text_turn, tool_turn


@pytest.fixture
def use_llm() -> Iterator[list[ScriptedLLM]]:
    """Call use_llm.append(ScriptedLLM(...)) to script the next model; the /chat endpoint gets it."""
    scripted: list[ScriptedLLM] = []
    app.dependency_overrides[get_llm] = lambda: scripted[-1]
    yield scripted


def test_chat_returns_answer_with_tool_calls_and_stores_the_turn(
    client: TestClient, db: Session, alice: User, use_llm: list[ScriptedLLM]
) -> None:
    order = make_order(db, alice.customer)  # type: ignore[arg-type]
    use_llm.append(
        ScriptedLLM(tool_turn(("get_order_status", {"order_id": str(order.id)})), text_turn(f"Order #{order.id} is on its way."))
    )

    response = client.post("/chat", json={"message": f"Where is order {order.id}?"}, headers=auth_header(alice))
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"conversation_id", "message_id", "message", "sources", "tool_calls", "latency_ms"}
    assert body["message"] == f"Order #{order.id} is on its way."
    assert body["tool_calls"][0]["name"] == "get_order_status" and body["tool_calls"][0]["status"] == "ok"
    assert body["sources"] == []

    messages = db.scalars(select(Message).where(Message.conversation_id == body["conversation_id"]).order_by(Message.id)).all()
    assert [m.role for m in messages] == [MessageRole.USER, MessageRole.ASSISTANT]
    assert messages[1].tool_calls and messages[1].latency_ms is not None

    stored = client.get(f"/conversations/{body['conversation_id']}", headers=auth_header(alice)).json()
    assert [m["role"] for m in stored["messages"]] == ["user", "assistant"]


def test_continuing_a_conversation_sends_the_history(client: TestClient, alice: User, use_llm: list[ScriptedLLM]) -> None:
    headers = auth_header(alice)
    use_llm.append(ScriptedLLM(text_turn("Hello Alice, how can I help?")))
    conversation_id = client.post("/chat", json={"message": "Hi"}, headers=headers).json()["conversation_id"]

    second = ScriptedLLM(text_turn("Sure."))
    use_llm.append(second)
    body = client.post("/chat", json={"conversation_id": conversation_id, "message": "Can you help me?"}, headers=headers).json()
    assert body["conversation_id"] == conversation_id
    assert second.calls[0]["messages"] == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello Alice, how can I help?"},
        {"role": "user", "content": "Can you help me?"},
    ]


def test_another_customers_conversation_is_not_found(client: TestClient, alice: User, bob: User, use_llm: list[ScriptedLLM]) -> None:
    use_llm.append(ScriptedLLM(text_turn("Hi Bob.")))
    bobs = client.post("/chat", json={"message": "Hi"}, headers=auth_header(bob)).json()["conversation_id"]
    use_llm.append(ScriptedLLM())
    response = client.post("/chat", json={"conversation_id": bobs, "message": "Show me this chat"}, headers=auth_header(alice))
    assert response.status_code == 404


def test_staff_cannot_use_the_customer_chat(client: TestClient, db: Session, use_llm: list[ScriptedLLM]) -> None:
    agent = make_staff(db, "agent@example.com", UserRole.AGENT)
    use_llm.append(ScriptedLLM())
    assert client.post("/chat", json={"message": "Hi"}, headers=auth_header(agent)).status_code == 403


def test_chat_input_validation_and_auth(client: TestClient, alice: User) -> None:
    headers = auth_header(alice)
    assert client.post("/chat", json={"message": "   "}, headers=headers).status_code == 422
    assert client.post("/chat", json={"message": "x" * 4001}, headers=headers).status_code == 422
    assert client.post("/chat", json={"message": "Hi"}).status_code == 401


def test_chat_without_llm_is_unavailable(client: TestClient, db: Session, alice: User) -> None:
    response = client.post("/chat", json={"message": "Hi"}, headers=auth_header(alice))
    assert response.status_code == 503
    assert db.scalars(select(Message)).first() is None  # nothing stored when the AI isn't available
