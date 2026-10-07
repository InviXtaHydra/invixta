from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Conversation, Message, MessageRole, User
from tests.conftest import auth_header


def make_conversation(db: Session, user: User) -> Conversation:
    conv = Conversation(customer_id=user.customer.id)  # type: ignore[union-attr]
    conv.messages.append(Message(role=MessageRole.USER, content="Where is my order?"))
    conv.messages.append(Message(role=MessageRole.ASSISTANT, content="Let me check."))
    db.add(conv)
    db.flush()
    return conv


def test_customer_sees_own_conversations_with_messages(client: TestClient, db: Session, alice: User) -> None:
    conv = make_conversation(db, alice)

    listed = client.get("/conversations", headers=auth_header(alice)).json()
    assert listed["total"] == 1
    assert listed["items"][0]["message_count"] == 2

    detail = client.get(f"/conversations/{conv.id}", headers=auth_header(alice)).json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]


def test_someone_elses_conversation_is_not_found(client: TestClient, db: Session, alice: User, bob: User) -> None:
    bobs = make_conversation(db, bob)
    assert client.get(f"/conversations/{bobs.id}", headers=auth_header(alice)).status_code == 404
    assert client.get("/conversations", headers=auth_header(alice)).json()["total"] == 0
