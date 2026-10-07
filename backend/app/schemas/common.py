from pydantic import BaseModel


class Page[T](BaseModel):
    """Paginated list response."""

    items: list[T]
    total: int
    limit: int
    offset: int
