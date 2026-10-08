"""Semantic search and the RAG service: real embeddings and pgvector, a scripted LLM."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agents.llm import get_llm
from app.main import app
from app.models import User
from app.rag.embeddings import Embedder
from app.rag.rag_service import NOT_FOUND_MESSAGE, RagService
from app.rag.retrieval import KnowledgeBaseSearch
from tests.conftest import auth_header, ingest
from tests.fakes import ScriptedLLM, text_turn
from tests.helpers_pdf import RETURNS_PDF_SECTIONS, SHIPPING_PDF_SECTIONS, make_pdf


def index_two_documents(db: Session, embedder: Embedder) -> None:
    ingest(db, embedder, "Return Policy.pdf", make_pdf(RETURNS_PDF_SECTIONS, title="Return Policy"))
    ingest(db, embedder, "Shipping Policy.pdf", make_pdf(SHIPPING_PDF_SECTIONS, title="Shipping Policy"))


def test_search_finds_the_right_document_with_metadata(db: Session, embedder: Embedder) -> None:
    index_two_documents(db, embedder)
    results = KnowledgeBaseSearch(db, embedder).search("How many days do I have to return a product?")
    assert results
    best = results[0]
    assert best.filename == "Return Policy.pdf"
    assert "30 days" in best.content
    assert best.page_number == 1
    assert best.document_id and best.chunk_id
    assert results == sorted(results, key=lambda r: r.score, reverse=True)

    shipping = KnowledgeBaseSearch(db, embedder).search("Do I pay shipping costs?")
    assert shipping[0].filename == "Shipping Policy.pdf"


def test_irrelevant_question_returns_nothing(db: Session, embedder: Embedder) -> None:
    index_two_documents(db, embedder)
    assert KnowledgeBaseSearch(db, embedder).search("Who painted the Mona Lisa?") == []


def test_search_endpoint(client: TestClient, db: Session, embedder: Embedder, alice: User) -> None:
    index_two_documents(db, embedder)
    response = client.get("/knowledge-base/search", params={"q": "refund time", "top_k": 2}, headers=auth_header(alice))
    assert response.status_code == 200
    results = response.json()["results"]
    assert 1 <= len(results) <= 2
    assert set(results[0]) >= {"document_id", "filename", "page_number", "chunk_id", "excerpt", "score"}
    assert client.get("/knowledge-base/search", params={"q": "refund"}).status_code == 401


def test_rag_answers_from_context_and_returns_cited_sources(db: Session, embedder: Embedder) -> None:
    index_two_documents(db, embedder)
    llm = ScriptedLLM(text_turn("You can return products within 30 days after delivery [1]."))
    result = RagService(db, embedder, llm).answer("How long do I have to return something?")

    assert result.answered
    assert "30 days" in result.answer
    assert len(result.sources) == 1 and result.sources[0].filename == "Return Policy.pdf"
    prompt = llm.calls[0]["messages"][0]["content"]
    assert "[1] (Return Policy.pdf, page 1)" in prompt  # the retrieved context was sent to the model
    assert "Only" in llm.calls[0]["system"] or "ONLY" in llm.calls[0]["system"]


def test_rag_does_not_call_the_llm_without_relevant_context(db: Session, embedder: Embedder) -> None:
    index_two_documents(db, embedder)
    llm = ScriptedLLM()  # would fail if called
    result = RagService(db, embedder, llm).answer("Who painted the Mona Lisa?")
    assert result.answer == NOT_FOUND_MESSAGE
    assert not result.answered and result.sources == []
    assert llm.calls == []


def test_rag_passes_on_the_models_not_found_answer(db: Session, embedder: Embedder) -> None:
    index_two_documents(db, embedder)
    llm = ScriptedLLM(text_turn(NOT_FOUND_MESSAGE))
    result = RagService(db, embedder, llm).answer("Can I return a product after 30 days for store credit?")
    assert result.answer == NOT_FOUND_MESSAGE
    assert result.sources == []


def test_ask_endpoint(client: TestClient, db: Session, embedder: Embedder, alice: User) -> None:
    index_two_documents(db, embedder)
    headers = auth_header(alice)
    assert (
        client.post("/knowledge-base/ask", json={"question": "How long do I have to return a product?"}, headers=headers).status_code == 503
    )

    app.dependency_overrides[get_llm] = lambda: ScriptedLLM(text_turn("Within 30 days of delivery [1]."))
    body = client.post("/knowledge-base/ask", json={"question": "How long do I have to return a product?"}, headers=headers).json()
    assert body["answered"] is True
    assert body["sources"][0]["filename"] == "Return Policy.pdf"


def test_ask_is_rate_limited_per_user(client: TestClient, db: Session, embedder: Embedder, alice: User) -> None:
    from app.core.rate_limit import chat_limiter

    index_two_documents(db, embedder)
    limiter = chat_limiter()
    original, limiter.limit = limiter.limit, 1
    try:
        app.dependency_overrides[get_llm] = lambda: ScriptedLLM(text_turn("Within 30 days [1]."))
        body = {"question": "How long do I have to return a product?"}
        assert client.post("/knowledge-base/ask", json=body, headers=auth_header(alice)).status_code == 200
        assert client.post("/knowledge-base/ask", json=body, headers=auth_header(alice)).status_code == 429
    finally:
        limiter.limit = original


def test_rag_can_rewrite_a_dutch_question_into_an_english_query(db: Session, embedder: Embedder) -> None:
    index_two_documents(db, embedder)
    llm = ScriptedLLM(text_turn("how many days to return a product"), text_turn("Binnen 30 dagen [1]."))
    result = RagService(db, embedder, llm, rewrite_query=True).answer("Hoeveel dagen heb ik om iets terug te sturen?")
    assert result.answered and result.sources[0].filename == "Return Policy.pdf"
    assert "Question: Hoeveel dagen" in llm.calls[1]["messages"][0]["content"]  # the model answers the original question
