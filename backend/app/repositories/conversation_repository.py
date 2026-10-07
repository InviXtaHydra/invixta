import builtins
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Conversation, Message, MessageRole


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, *, customer_id: int | None, limit: int = 20, offset: int = 0) -> list[tuple[Conversation, int, str | None]]:
        """Conversations (newest activity first) with their message count and first user message (the title)."""
        count = select(func.count(Message.id)).where(Message.conversation_id == Conversation.id).correlate(Conversation).scalar_subquery()
        first_question = (
            select(Message.content)
            .where(Message.conversation_id == Conversation.id, Message.role == MessageRole.USER)
            .order_by(Message.id)
            .limit(1)
            .correlate(Conversation)
            .scalar_subquery()
        )
        query = select(Conversation, count, first_question).order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        if customer_id is not None:
            query = query.where(Conversation.customer_id == customer_id)
        return [(conv, n, title) for conv, n, title in self.db.execute(query.limit(limit).offset(offset))]

    def count(self, *, customer_id: int | None) -> int:
        query = select(func.count()).select_from(Conversation)
        if customer_id is not None:
            query = query.where(Conversation.customer_id == customer_id)
        return self.db.scalar(query) or 0

    def get(self, conversation_id: int, *, customer_id: int | None) -> Conversation | None:
        query = select(Conversation).options(selectinload(Conversation.messages)).where(Conversation.id == conversation_id)
        if customer_id is not None:
            query = query.where(Conversation.customer_id == customer_id)
        return self.db.scalar(query)

    def create(self, customer_id: int) -> Conversation:
        conversation = Conversation(customer_id=customer_id)
        self.db.add(conversation)
        self.db.flush()
        return conversation

    def recent_messages(self, conversation_id: int, limit: int) -> Sequence[Message]:
        """The last `limit` user/assistant messages, oldest first."""
        rows = self.db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.role.in_([MessageRole.USER, MessageRole.ASSISTANT]))
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
        return builtins.list(reversed(builtins.list(rows)))

    def add_message(
        self,
        conversation: Conversation,
        role: MessageRole,
        content: str,
        *,
        tool_calls: builtins.list[dict[str, Any]] | None = None,
        sources: builtins.list[dict[str, Any]] | None = None,
        latency_ms: int | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation.id, role=role, content=content, tool_calls=tool_calls, sources=sources, latency_ms=latency_ms
        )
        self.db.add(message)
        conversation.updated_at = datetime.now(UTC)  # bump "last activity"
        self.db.flush()
        return message
