from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import Conversation, User
from app.repositories.conversation_repository import ConversationRepository
from app.services.access import customer_scope


class ConversationService:
    def __init__(self, db: Session) -> None:
        self.conversations = ConversationRepository(db)

    def list_conversations(self, user: User, *, limit: int, offset: int) -> tuple[list[tuple[Conversation, int, str | None]], int]:
        scope = customer_scope(user)
        return self.conversations.list(customer_id=scope, limit=limit, offset=offset), self.conversations.count(customer_id=scope)

    def get_conversation(self, user: User, conversation_id: int) -> Conversation:
        conversation = self.conversations.get(conversation_id, customer_id=customer_scope(user))
        if conversation is None:
            raise NotFoundError(f"Conversation {conversation_id} not found")
        return conversation
