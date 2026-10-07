from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Conversation, Message


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, *, customer_id: int | None, limit: int = 20, offset: int = 0) -> list[tuple[Conversation, int]]:
        """Conversations (newest activity first) with their message count."""
        count = select(func.count(Message.id)).where(Message.conversation_id == Conversation.id).correlate(Conversation).scalar_subquery()
        query = select(Conversation, count).order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        if customer_id is not None:
            query = query.where(Conversation.customer_id == customer_id)
        return [(conv, n) for conv, n in self.db.execute(query.limit(limit).offset(offset))]

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
