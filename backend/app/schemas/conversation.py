from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import MessageRole


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: MessageRole
    content: str
    created_at: datetime


class ConversationSummary(BaseModel):
    id: int
    customer_id: int
    created_at: datetime
    updated_at: datetime
    message_count: int


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRead]
