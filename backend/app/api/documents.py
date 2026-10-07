from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.exceptions import NotFoundError, PayloadTooLargeError
from app.models import Document, User, UserRole
from app.rag.embeddings import Embedder, get_embedder
from app.rag.ingestion import IngestionService
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import ChunkRead, DocumentDetail, DocumentRead

router = APIRouter(prefix="/documents", tags=["knowledge base (admin)"])
admin_only = require_roles(UserRole.ADMIN)


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="A PDF, max. 10 MB"),
    user: User = Depends(admin_only),
    db: Session = Depends(get_db),
    embedder: Embedder = Depends(get_embedder),
) -> DocumentRead:
    """Upload a PDF and index it: text extraction → cleaning → chunking → embeddings → pgvector."""
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)  # never read more than the limit into memory
    if len(data) > max_bytes:
        raise PayloadTooLargeError(f"The file is larger than {get_settings().max_upload_mb} MB")
    document, chunk_count = IngestionService(db, embedder).ingest_pdf(filename=file.filename, data=data, uploaded_by_id=user.id)
    return _read(document, chunk_count)


@router.get("", response_model=list[DocumentRead])
def list_documents(_: User = Depends(admin_only), db: Session = Depends(get_db)) -> list[DocumentRead]:
    return [_read(doc, n) for doc, n in DocumentRepository(db).list_with_chunk_counts()]


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: int, _: User = Depends(admin_only), db: Session = Depends(get_db)) -> DocumentDetail:
    document = DocumentRepository(db).get(document_id)
    if document is None:
        raise NotFoundError(f"Document {document_id} not found")
    chunks = [
        ChunkRead(id=c.id, chunk_index=c.chunk_index, page_number=c.page_number, content=c.content, created_at=c.created_at)
        for c in document.chunks
    ]
    return DocumentDetail(**_read(document, len(chunks)).model_dump(), chunks=chunks)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int, _: User = Depends(admin_only), db: Session = Depends(get_db), embedder: Embedder = Depends(get_embedder)
) -> Response:
    IngestionService(db, embedder).delete(document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _read(document: Document, chunk_count: int) -> DocumentRead:
    return DocumentRead(
        id=document.id,
        filename=document.filename,
        uploaded_at=document.uploaded_at,
        page_count=document.page_count,
        size_bytes=document.size_bytes,
        chunk_count=chunk_count,
    )
