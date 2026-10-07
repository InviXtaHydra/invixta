"""PDF ingestion and the admin document endpoints, with the real embedding model and pgvector."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DocumentChunk, User, UserRole
from app.rag.embeddings import Embedder
from app.rag.ingestion import safe_filename
from tests.conftest import auth_header, make_staff
from tests.helpers_pdf import RETURNS_PDF_SECTIONS, make_blank_pdf, make_pdf


def upload(client: TestClient, user: User, data: bytes, filename: str = "Returns.pdf"):  # type: ignore[no-untyped-def]
    return client.post("/documents", files={"file": (filename, data, "application/pdf")}, headers=auth_header(user))


def test_admin_uploads_a_pdf_and_chunks_are_embedded(client: TestClient, db: Session, embedder: Embedder) -> None:
    admin = make_staff(db, "admin@example.com", UserRole.ADMIN)
    response = upload(client, admin, make_pdf(RETURNS_PDF_SECTIONS, title="Return Policy", pages=2))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["filename"] == "Returns.pdf"
    assert body["page_count"] == 2
    assert body["chunk_count"] >= 4

    chunks = db.scalars(select(DocumentChunk).where(DocumentChunk.document_id == body["id"]).order_by(DocumentChunk.chunk_index)).all()
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert {c.page_number for c in chunks} == {1, 2}
    assert chunks[0].content.startswith("Return Policy: ")
    assert any(c.content.startswith("Return window: ") for c in chunks)  # each chunk carries its section heading
    assert all(c.embedding is not None and len(c.embedding) == 384 for c in chunks)


def test_document_list_detail_and_delete(client: TestClient, db: Session) -> None:
    admin = make_staff(db, "admin@example.com", UserRole.ADMIN)
    headers = auth_header(admin)
    document_id = upload(client, admin, make_pdf(RETURNS_PDF_SECTIONS)).json()["id"]

    listed = client.get("/documents", headers=headers).json()
    assert [d["id"] for d in listed] == [document_id]

    detail = client.get(f"/documents/{document_id}", headers=headers).json()
    assert detail["chunks"] and detail["chunks"][0]["page_number"] == 1

    assert client.delete(f"/documents/{document_id}", headers=headers).status_code == 204
    assert client.get(f"/documents/{document_id}", headers=headers).status_code == 404
    assert db.scalars(select(DocumentChunk).where(DocumentChunk.document_id == document_id)).first() is None


def test_same_file_twice_is_a_conflict(client: TestClient, db: Session) -> None:
    admin = make_staff(db, "admin@example.com", UserRole.ADMIN)
    data = make_pdf(RETURNS_PDF_SECTIONS)
    assert upload(client, admin, data).status_code == 201
    assert upload(client, admin, data, filename="copy.pdf").status_code == 409


def test_non_pdf_and_too_large_files_are_rejected(client: TestClient, db: Session) -> None:
    admin = make_staff(db, "admin@example.com", UserRole.ADMIN)
    assert upload(client, admin, b"just some text", filename="fake.pdf").status_code == 415
    too_big = b"%PDF-1.4\n" + b"0" * (10 * 1024 * 1024 + 1)
    assert upload(client, admin, too_big).status_code == 413


def test_pdf_without_text_is_rejected(client: TestClient, db: Session) -> None:
    admin = make_staff(db, "admin@example.com", UserRole.ADMIN)
    assert upload(client, admin, make_blank_pdf()).status_code == 400


def test_only_admins_manage_documents(client: TestClient, db: Session, alice: User) -> None:
    agent = make_staff(db, "agent@example.com", UserRole.AGENT)
    data = make_pdf(RETURNS_PDF_SECTIONS)
    assert upload(client, alice, data).status_code == 403
    assert upload(client, agent, data).status_code == 403
    assert client.get("/documents", headers=auth_header(alice)).status_code == 403


def test_safe_filename_strips_paths_and_control_characters() -> None:
    assert safe_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert safe_filename("C:\\Users\\me\\Policy.pdf") == "Policy.pdf"
    assert safe_filename("bad\x00name.pdf") == "badname.pdf"
    assert safe_filename(None) == "document.pdf"
