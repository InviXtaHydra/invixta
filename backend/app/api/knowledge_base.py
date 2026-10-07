from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.rag.embeddings import Embedder, get_embedder
from app.rag.retrieval import KnowledgeBaseSearch
from app.schemas.knowledge_base import SearchResponse, SourceRead

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
