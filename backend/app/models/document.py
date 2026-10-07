from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.core.database import Base
from app.models.mixins import CreatedAtMixin


class Document(Base):
    """An uploaded knowledge-base document (PDF). Filled by the ingestion pipeline in phase 2."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(CreatedAtMixin, Base):
    """A piece of a document plus its embedding vector, used for semantic search (pgvector)."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        # HNSW index for fast approximate nearest-neighbour search with cosine distance.
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    page_number: Mapped[int | None]
    embedding: Mapped[list[float] | None] = mapped_column(Vector(get_settings().embedding_dim))

    document: Mapped["Document"] = relationship(back_populates="chunks")
