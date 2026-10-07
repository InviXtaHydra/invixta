from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_with_chunk_counts(self) -> list[tuple[Document, int]]:
        count = select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == Document.id).correlate(Document).scalar_subquery()
        rows = self.db.execute(select(Document, count).order_by(Document.uploaded_at.desc(), Document.id.desc()))
        return [(doc, n) for doc, n in rows]

    def get(self, document_id: int) -> Document | None:
        return self.db.get(Document, document_id)

    def get_by_sha256(self, sha256: str) -> Document | None:
        return self.db.scalar(select(Document).where(Document.sha256 == sha256))

    def chunk_count(self, document_id: int) -> int:
        return self.db.scalar(select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == document_id)) or 0

    def add(self, document: Document) -> Document:
        self.db.add(document)
        self.db.flush()
        return document

    def delete(self, document: Document) -> None:
        self.db.delete(document)  # chunks are removed by ON DELETE CASCADE
        self.db.flush()
