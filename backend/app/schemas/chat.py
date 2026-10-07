from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.schemas.knowledge_base import SourceRead


class ChatRequest(BaseModel):
    conversation_id: int | None = Field(default=None, description="Leave out to start a new conversation")
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message can't be empty")
        return value


class ToolCallRead(BaseModel):
    name: str
    arguments: dict[str, Any]
    status: str
    summary: str
    duration_ms: int


class ChatResponse(BaseModel):
    conversation_id: int
    message_id: int
    message: str
    sources: list[SourceRead]
    tool_calls: list[ToolCallRead]
    latency_ms: int
