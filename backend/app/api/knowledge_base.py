from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.agents.llm import LLMClient, get_llm, require_llm
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.rag.embeddings import Embedder, get_embedder
from app.rag.rag_service import RagService
from app.rag.retrieval import KnowledgeBaseSearch
from app.schemas.knowledge_base import AskRequest, AskResponse, SearchResponse, SourceRead

router = APIRouter(prefix="/knowledge-base", tags=["knowledge base"])


@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(min_length=3, max_length=1000, description="Question or search terms"),
    top_k: int = Query(5, ge=1, le=20),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    embedder: Embedder = Depends(get_embedder),
) -> SearchResponse:
    """Semantic search: the most relevant document chunks for a question, with their sources."""
    results = KnowledgeBaseSearch(db, embedder).search(q, top_k=top_k)
    return SearchResponse(query=q, results=[SourceRead.model_validate(r.as_source()) for r in results])


@router.post("/ask", response_model=AskResponse, responses={503: {"description": "No LLM configured"}})
def ask(
    body: AskRequest,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    embedder: Embedder = Depends(get_embedder),
    llm: LLMClient | None = Depends(get_llm),
) -> AskResponse:
    """RAG answer: retrieve relevant chunks, let the LLM answer from them only, and return the sources."""
    result = RagService(db, embedder, require_llm(llm)).answer(body.question)
    return AskResponse(
        question=body.question,
        answer=result.answer,
        sources=[SourceRead.model_validate(s.as_source()) for s in result.sources],
        answered=result.answered,
    )
