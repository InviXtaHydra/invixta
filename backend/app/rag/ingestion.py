"""Ingestion pipeline: PDF → text per page → cleaning → chunks → embeddings → pgvector."""

import hashlib
import logging
import re
import time
from pathlib import PurePath

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError, PayloadTooLargeError, UnsupportedMediaTypeError
from app.models import Document, DocumentChunk
from app.rag.embeddings import Embedder
from app.rag.pdf import extract_pages
from app.rag.text_processing import chunk_page
from app.repositories.document_repository import DocumentRepository

logger = logging.getLogger("supportai.rag")


def safe_filename(name: str | None) -> str:
    """Keep only the base name, without path parts or control characters."""
    base = PurePath((name or "document.pdf").replace("\\", "/")).name
    base = re.sub(r"[\x00-\x1f\x7f]", "", base).strip() or "document.pdf"
    return base[:255]


class IngestionService:
    def __init__(self, db: Session, embedder: Embedder) -> None:
        self.db = db
        self.embedder = embedder
        self.documents = DocumentRepository(db)
        self.settings = get_settings()

    def ingest_pdf(self, *, filename: str | None, data: bytes, uploaded_by_id: int | None = None) -> tuple[Document, int]:
        """Validate, chunk and embed a PDF. Returns the document and its number of chunks."""
        started = time.perf_counter()
        name = safe_filename(filename)
        max_bytes = self.settings.max_upload_mb * 1024 * 1024
        if len(data) > max_bytes:
            raise PayloadTooLargeError(f"The file is larger than {self.settings.max_upload_mb} MB")
        if not data.startswith(b"%PDF-"):  # check the content, not just the file extension
            raise UnsupportedMediaTypeError("Only PDF files are supported")

        sha256 = hashlib.sha256(data).hexdigest()
        if self.documents.get_by_sha256(sha256):
            raise ConflictError("This document has already been uploaded")

        pages = extract_pages(data, self.settings.max_pdf_pages)
        chunks: list[tuple[int, str]] = []  # (page number, text)
        for page_number, raw in enumerate(pages, start=1):
            for piece in chunk_page(raw):
                chunks.append((page_number, piece))
        if not chunks:
            raise BadRequestError("No text could be extracted from this PDF (is it a scanned image?)")

        vectors = self.embedder.embed_documents([text for _, text in chunks])
        document = Document(filename=name, sha256=sha256, page_count=len(pages), size_bytes=len(data), uploaded_by_id=uploaded_by_id)
        document.chunks = [
            DocumentChunk(chunk_index=i, page_number=page, content=text, embedding=vector)
            for i, ((page, text), vector) in enumerate(zip(chunks, vectors, strict=True))
        ]
        self.documents.add(document)
        self.db.commit()
        logger.info(
            "document ingested",
            extra={"document_id": document.id, "pages": len(pages), "chunks": len(chunks), "duration_ms": _ms(started)},
        )
        return document, len(chunks)

    def delete(self, document_id: int) -> None:
        document = self.documents.get(document_id)
        if document is None:
            raise NotFoundError(f"Document {document_id} not found")
        self.documents.delete(document)
        self.db.commit()
        logger.info("document deleted", extra={"document_id": document_id})


def _ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
