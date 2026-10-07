"""Semantic search over the knowledge base with pgvector.

The question is embedded with the same model as the documents; pgvector then returns the chunks
whose vectors are closest by cosine distance (`<=>`), using the HNSW index. score = 1 - distance,
so 1.0 means "same meaning" and chunks below `min_score` are treated as not relevant.
"""

import logging
import time
from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Document, DocumentChunk
from app.rag.embeddings import Embedder

logger = logging.getLogger("supportai.rag")


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    document_id: int
    filename: str
    page_number: int | None
    chunk_index: int
    content: str
    score: float

    def as_source(self) -> dict[str, object]:
        """Source metadata shown to the user (without the full text)."""
        data = asdict(self)
        data["excerpt"] = data.pop("content")[:300]
        data["score"] = round(self.score, 3)
        return data


class KnowledgeBaseSearch:
    def __init__(self, db: Session, embedder: Embedder) -> None:
        self.db = db
        self.embedder = embedder

    def search(self, query: str, *, top_k: int | None = None, min_score: float | None = None) -> list[RetrievedChunk]:
        """Return up to top_k relevant chunks, best match first."""
        settings = get_settings()
        top_k = top_k or settings.rag_top_k
        min_score = settings.rag_min_score if min_score is None else min_score
        started = time.perf_counter()

        vector = self.embedder.embed_query(query)
        distance = DocumentChunk.embedding.cosine_distance(vector).label("distance")
        rows = self.db.execute(
            select(DocumentChunk, Document.filename, distance)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.embedding.is_not(None))
            .order_by(distance)
            .limit(top_k)
        ).all()

        results = [
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                filename=filename,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                score=1.0 - float(dist),
            )
            for chunk, filename, dist in rows
        ]
        relevant = [r for r in results if r.score >= min_score]
        # Log what was retrieved, not the question itself (it may contain personal details).
        logger.info(
            "knowledge base search",
            extra={
                "query_chars": len(query),
                "top_k": top_k,
                "candidates": len(results),
                "relevant": len(relevant),
                "best_score": round(results[0].score, 3) if results else None,
                "documents": sorted({r.document_id for r in relevant}),
                "duration_ms": round((time.perf_counter() - started) * 1000),
            },
        )
        return relevant
