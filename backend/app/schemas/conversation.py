from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MessageRole


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: MessageRole
    content: str
    created_at: datetime
    tool_calls: list[dict[str, Any]] | None = None
    sources: list[dict[str, Any]] | None = None
    latency_ms: int | None = None


class ConversationSummary(BaseModel):
    id: int
    customer_id: int
    created_at: datetime
    updated_at: datetime
    message_count: int
    title: str | None = Field(default=None, description="The first question in the conversation, shortened")


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRead]
