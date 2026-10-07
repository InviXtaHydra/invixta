from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, UserRole
from tests.conftest import auth_header, make_staff, make_ticket

TICKET = {"subject": "Parcel arrived damaged", "description": "The box was crushed and the mug inside is broken.", "priority": "high"}


def test_customer_creates_a_ticket_for_themselves(client: TestClient, alice: User) -> None:
    response = client.post("/tickets", json=TICKET, headers=auth_header(alice))
    assert response.status_code == 201
    body = response.json()
    assert body["customer_id"] == alice.customer.id  # type: ignore[union-attr]
    assert body["status"] == "open"
    assert body["priority"] == "high"

    listed = client.get("/tickets", headers=auth_header(alice)).json()
    assert [t["id"] for t in listed["items"]] == [body["id"]]


def test_priority_defaults_to_medium(client: TestClient, alice: User) -> None:
    body = client.post(
        "/tickets", json={"subject": "Question", "description": "When will my order arrive?"}, headers=auth_header(alice)
    ).json()
    assert body["priority"] == "medium"


def test_ticket_input_is_validated(client: TestClient, alice: User) -> None:
    headers = auth_header(alice)
    assert client.post("/tickets", json={**TICKET, "subject": "Hi"}, headers=headers).status_code == 422
    assert client.post("/tickets", json={**TICKET, "description": "short"}, headers=headers).status_code == 422
    assert client.post("/tickets", json={**TICKET, "priority": "whenever"}, headers=headers).status_code == 422
    assert client.post("/tickets", json={**TICKET, "status": "closed"}, headers=headers).json().get("status") in (None, "open")


def test_customer_cannot_open_a_ticket_for_someone_else(client: TestClient, alice: User, bob: User) -> None:
    response = client.post("/tickets", json={**TICKET, "customer_id": bob.customer.id}, headers=auth_header(alice))  # type: ignore[union-attr]
    assert response.status_code == 403


def test_customer_only_sees_their_own_tickets(client: TestClient, db: Session, alice: User, bob: User) -> None:
    make_ticket(db, alice.customer, "Alice's ticket")  # type: ignore[arg-type]
    bobs = make_ticket(db, bob.customer, "Bob's ticket")  # type: ignore[arg-type]

    listed = client.get("/tickets", headers=auth_header(alice)).json()
    assert [t["subject"] for t in listed["items"]] == ["Alice's ticket"]
    assert client.get(f"/tickets/{bobs.id}", headers=auth_header(alice)).status_code == 404
    assert client.get(f"/tickets/{bobs.id}", headers=auth_header(bob)).status_code == 200


def test_agent_opens_a_ticket_on_behalf_of_a_customer(client: TestClient, db: Session, alice: User) -> None:
    agent = make_staff(db, "agent@example.com", UserRole.AGENT)

    created = client.post("/tickets", json={**TICKET, "customer_id": alice.customer.id}, headers=auth_header(agent))  # type: ignore[union-attr]
    assert created.status_code == 201
    assert created.json()["customer_id"] == alice.customer.id  # type: ignore[union-attr]

    assert client.post("/tickets", json=TICKET, headers=auth_header(agent)).status_code == 403  # customer_id required
    assert client.post("/tickets", json={**TICKET, "customer_id": 999999}, headers=auth_header(agent)).status_code == 404


def test_tickets_require_authentication(client: TestClient) -> None:
    assert client.get("/tickets").status_code == 401
    assert client.post("/tickets", json=TICKET).status_code == 401
