"""Index PDFs into the knowledge base with the same pipeline as the upload endpoint.

    docker compose exec backend python scripts/ingest_documents.py              # sample_documents/
    docker compose exec backend python scripts/ingest_documents.py path/to/dir  # another folder

Documents that are already indexed (same file content) are skipped.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.core.exceptions import ConflictError
from app.rag.embeddings import get_embedder
from app.rag.ingestion import IngestionService

DEFAULT_DIR = Path(__file__).resolve().parent.parent / "sample_documents"


def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DIR
    pdfs = sorted(folder.glob("*.pdf"))
    if not pdfs:
        sys.exit(f"No PDF files found in {folder}")
    embedder = get_embedder()
    with SessionLocal() as db:
        service = IngestionService(db, embedder)
        for path in pdfs:
            try:
                document, chunks = service.ingest_pdf(filename=path.name, data=path.read_bytes())
                print(f"indexed  {path.name}: {document.page_count} pages, {chunks} chunks")
            except ConflictError:
                db.rollback()
                print(f"skipped  {path.name}: already indexed")


if __name__ == "__main__":
    main()
