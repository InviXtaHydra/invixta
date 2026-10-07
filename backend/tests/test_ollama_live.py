"""Optional: the real agent with the real local model in Ollama. Skipped when Ollama isn't running or
the model isn't pulled (as in CI). Run it on your machine to check that the model uses the tools:

    docker compose exec backend pytest tests/test_ollama_live.py -v

Model answers vary, so the checks are about behaviour (which tool, which data), not exact words.
"""

import pytest
from sqlalchemy.orm import Session

from app.agents.llm import get_llm
from app.agents.ollama_client import OllamaClient
from app.agents.support_agent import SupportAgent
from app.models import User
from app.rag.embeddings import Embedder
from app.tools.support_tools import SupportTools
from tests.conftest import make_order


@pytest.fixture
def live_llm() -> OllamaClient:
    llm = get_llm()
    if not isinstance(llm, OllamaClient) or llm.status() != "ok":
        pytest.skip("Ollama isn't running with the configured model")
    return llm


def test_real_model_looks_up_the_order(db: Session, embedder: Embedder, alice: User, live_llm: OllamaClient) -> None:
    order = make_order(db, alice.customer)  # type: ignore[arg-type]
    result = SupportAgent(live_llm, SupportTools(db, alice, embedder), alice).run([], f"Where is my order #{order.id}?")
    assert "get_order_status" in [c.name for c in result.tool_calls]
    assert "shipped" in result.text.lower() or "PO123456789" in result.text
