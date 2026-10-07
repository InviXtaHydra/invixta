from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas.common import Page
from app.schemas.conversation import ConversationRead, ConversationSummary
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=Page[ConversationSummary])
def list_conversations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[ConversationSummary]:
    rows, total = ConversationService(db).list_conversations(user, limit=limit, offset=offset)
    items = [
        ConversationSummary(id=c.id, customer_id=c.customer_id, created_at=c.created_at, updated_at=c.updated_at, message_count=n)
        for c, n in rows
    ]
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{conversation_id}", response_model=ConversationRead, responses={404: {"description": "Conversation not found (or not yours)"}}
)
def get_conversation(conversation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ConversationRead:
    return ConversationRead.model_validate(ConversationService(db).get_conversation(user, conversation_id))
