"""The rule-based LLM stand-in used by the browser end-to-end test, run through the real agent."""

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.agents.scripted_llm import ScriptedSupportLLM
from app.agents.support_agent import SupportAgent
from app.core.config import Settings
from app.models import User
from app.rag.embeddings import Embedder
from app.rag.rag_service import NOT_FOUND_MESSAGE
from app.tools.support_tools import SupportTools
from tests.conftest import ingest, make_order
from tests.helpers_pdf import RETURNS_PDF_SECTIONS, make_pdf


def ask(db: Session, user: User, embedder: Embedder, message: str) -> tuple[str, list[str]]:
    streamed: list[str] = []
    agent = SupportAgent(ScriptedSupportLLM(delay_seconds=0), SupportTools(db, user, embedder), user)
    result = agent.run([], message, on_event=lambda e: streamed.append(e["delta"]) if e["type"] == "text" else None)
    assert "".join(streamed) == result.text
    return result.text, [c.name for c in result.tool_calls]


def test_order_question_uses_the_order_tool(db: Session, embedder: Embedder, alice: User) -> None:
    order = make_order(db, alice.customer)  # type: ignore[arg-type]
    text, tools = ask(db, alice, embedder, f"Where is order #{order.id}?")
    assert tools == ["get_order_status"]
    assert text.startswith(f"Order #{order.id} is currently shipped.") and "PO123456789" in text


def test_someone_elses_order_is_not_found(db: Session, embedder: Embedder, alice: User, bob: User) -> None:
    order = make_order(db, bob.customer)  # type: ignore[arg-type]
    text, _ = ask(db, alice, embedder, f"Where is order {order.id}?")
    assert "not found" in text.lower() and "PO123456789" not in text


def test_policy_question_searches_the_knowledge_base(db: Session, embedder: Embedder, alice: User) -> None:
    ingest(db, embedder, "Return Policy.pdf", make_pdf(RETURNS_PDF_SECTIONS, title="Return Policy"))
    text, tools = ask(db, alice, embedder, "How many days do I have to return a product?")
    assert tools == ["search_knowledge_base"]
    assert "Return Policy.pdf" in text and "30 days" in text
    assert ask(db, alice, embedder, "Who painted the Mona Lisa?")[0] == NOT_FOUND_MESSAGE


def test_damaged_item_opens_a_ticket(db: Session, embedder: Embedder, alice: User) -> None:
    order = make_order(db, alice.customer)  # type: ignore[arg-type]
    text, tools = ask(db, alice, embedder, f"Order {order.id} arrived damaged")
    assert tools == ["create_support_ticket"] and "opened ticket #" in text


def test_scripted_llm_is_refused_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", llm_provider="scripted", database_url="postgresql://x", jwt_secret_key="x" * 32)


def test_placeholder_jwt_secret_is_refused_in_production() -> None:
    placeholder = "change-me-to-a-long-random-string"
    with pytest.raises(ValidationError):
        Settings(environment="production", database_url="postgresql://x", jwt_secret_key=placeholder)
    Settings(environment="development", database_url="postgresql://x", jwt_secret_key=placeholder)  # fine locally
    with pytest.raises(ValidationError):
        Settings(database_url="postgresql://x", jwt_secret_key="too-short")
