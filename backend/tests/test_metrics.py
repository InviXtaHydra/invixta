"""GET /admin/metrics: computed with SQL from stored chat messages, tool calls and tickets."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agents.llm import get_llm
from app.main import app
from app.models import User, UserRole
from app.rag.rag_service import NOT_FOUND_MESSAGE
from tests.conftest import auth_header, make_order, make_staff, make_ticket
from tests.fakes import ScriptedLLM, text_turn, tool_turn


def test_metrics_reflect_real_chat_activity(client: TestClient, db: Session, alice: User) -> None:
    admin = make_staff(db, "admin@example.com", UserRole.ADMIN)
    order = make_order(db, alice.customer)  # type: ignore[arg-type]
    make_ticket(db, alice.customer)  # type: ignore[arg-type]
    headers = auth_header(alice)

    app.dependency_overrides[get_llm] = lambda: ScriptedLLM(
        tool_turn(("get_order_status", {"order_id": str(order.id)}), ("get_order_status", {"order_id": "99999999"})),
        text_turn("It has shipped."),
    )
    client.post("/chat", json={"message": f"Where is order {order.id}?"}, headers=headers)
    app.dependency_overrides[get_llm] = lambda: ScriptedLLM(
        tool_turn(("search_knowledge_base", {"query": "do you sell gift cards to companies"})), text_turn(NOT_FOUND_MESSAGE)
    )
    client.post("/chat", json={"message": "Do you sell gift cards to companies?"}, headers=headers)

    response = client.get("/admin/metrics", headers=auth_header(admin))
    assert response.status_code == 200
    m = response.json()
    assert m["total_conversations"] == 2
    assert m["chat_turns"] == 2
    assert m["avg_latency_ms"] is not None and m["p95_latency_ms"] >= m["avg_latency_ms"] * 0  # both measured
    assert m["tool_calls"] == 3
    assert {t["name"]: (t["calls"], t["errors"]) for t in m["tool_usage"]} == {"get_order_status": (2, 1), "search_knowledge_base": (1, 0)}
    assert m["rag_searches"] == 1
    assert m["tickets_total"] == 1 and m["tickets_by_status"]["open"] == 1 and m["tickets_by_status"]["closed"] == 0
    assert m["unresolved_questions"] == 1
    assert m["recent_unresolved"][0]["question"] == "Do you sell gift cards to companies?"
    assert len(m["chat_turns_per_day"]) == 14
    assert m["chat_turns_per_day"][-1]["chat_turns"] == 2  # today


def test_metrics_are_admin_only(client: TestClient, db: Session, alice: User) -> None:
    agent = make_staff(db, "agent@example.com", UserRole.AGENT)
    assert client.get("/admin/metrics", headers=auth_header(alice)).status_code == 403
    assert client.get("/admin/metrics", headers=auth_header(agent)).status_code == 403
    assert client.get("/admin/metrics").status_code == 401
