"""Password change, login rate limiting, staff ticket updates and conversation titles."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agents.llm import get_llm
from app.main import app
from app.models import User, UserRole
from tests.conftest import PASSWORD, auth_header, make_staff, make_ticket
from tests.fakes import ScriptedLLM, text_turn


def login(client: TestClient, email: str, password: str) -> int:
    return client.post("/auth/login", data={"username": email, "password": password}).status_code


def test_change_password(client: TestClient, alice: User) -> None:
    headers = auth_header(alice)
    wrong = client.post("/users/me/password", json={"current_password": "nope", "new_password": "NewSecret123"}, headers=headers)
    assert wrong.status_code == 400
    same = client.post("/users/me/password", json={"current_password": PASSWORD, "new_password": PASSWORD}, headers=headers)
    assert same.status_code == 400
    short = client.post("/users/me/password", json={"current_password": PASSWORD, "new_password": "short"}, headers=headers)
    assert short.status_code == 422

    ok = client.post("/users/me/password", json={"current_password": PASSWORD, "new_password": "NewSecret123"}, headers=headers)
    assert ok.status_code == 204
    assert login(client, "alice@example.com", PASSWORD) == 401
    assert login(client, "alice@example.com", "NewSecret123") == 200


def test_repeated_failed_logins_are_blocked(client: TestClient, alice: User, bob: User) -> None:
    for _ in range(10):
        assert login(client, "alice@example.com", "wrong-password") == 401
    blocked = client.post("/auth/login", data={"username": "alice@example.com", "password": PASSWORD})
    assert blocked.status_code == 429  # even the right password, until the window has passed
    assert "Retry-After" in blocked.headers
    assert login(client, "bob@example.com", PASSWORD) == 200  # other accounts aren't affected


def test_successful_logins_are_not_limited(client: TestClient, alice: User) -> None:
    for _ in range(12):
        assert login(client, "alice@example.com", PASSWORD) == 200


def test_staff_update_ticket_status_and_priority(client: TestClient, db: Session, alice: User) -> None:
    agent = make_staff(db, "agent@example.com", UserRole.AGENT)
    ticket = make_ticket(db, alice.customer)  # type: ignore[arg-type]
    response = client.patch(f"/tickets/{ticket.id}", json={"status": "in_progress", "priority": "urgent"}, headers=auth_header(agent))
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress" and response.json()["priority"] == "urgent"
    assert client.get(f"/tickets/{ticket.id}", headers=auth_header(alice)).json()["status"] == "in_progress"

    assert client.patch(f"/tickets/{ticket.id}", json={"status": "done"}, headers=auth_header(agent)).status_code == 422
    assert client.patch("/tickets/999999", json={"status": "closed"}, headers=auth_header(agent)).status_code == 404


def test_customers_cannot_update_tickets(client: TestClient, alice: User) -> None:
    ticket_id = client.post(
        "/tickets", json={"subject": "Broken mug", "description": "The mug arrived broken."}, headers=auth_header(alice)
    ).json()["id"]
    assert client.patch(f"/tickets/{ticket_id}", json={"status": "closed"}, headers=auth_header(alice)).status_code == 403


def test_conversation_list_has_a_title(client: TestClient, alice: User) -> None:
    app.dependency_overrides[get_llm] = lambda: ScriptedLLM(text_turn("We ship to all EU countries."))
    question = "Do you ship to Germany? " + "I'd like to order a lamp for my office and want to know before I order it."
    client.post("/chat", json={"message": question}, headers=auth_header(alice))
    [conversation] = client.get("/conversations", headers=auth_header(alice)).json()["items"]
    assert conversation["title"].startswith("Do you ship to Germany?")
    assert len(conversation["title"]) <= 80 and conversation["title"].endswith("…")
