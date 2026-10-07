from pydantic import BaseModel, Field


class SourceRead(BaseModel):
    """A knowledge-base chunk used as a source for an answer."""

    chunk_id: int
    document_id: int
    filename: str
    page_number: int | None
    chunk_index: int
    score: float = Field(description="Cosine similarity between question and chunk (0 to 1)")
    excerpt: str


class SearchResponse(BaseModel):
    query: str
    results: list[SourceRead]


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceRead]
    answered: bool = Field(description="False when the knowledge base didn't contain enough information")
