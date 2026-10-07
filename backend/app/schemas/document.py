from datetime import datetime

from pydantic import BaseModel


class DocumentRead(BaseModel):
    id: int
    filename: str
    uploaded_at: datetime
    page_count: int
    size_bytes: int
    chunk_count: int


class ChunkRead(BaseModel):
    id: int
    chunk_index: int
    page_number: int | None
    content: str
    created_at: datetime


class DocumentDetail(DocumentRead):
    chunks: list[ChunkRead]
