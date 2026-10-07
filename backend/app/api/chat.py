from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.llm import LLMClient, get_llm, require_llm
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.rag.embeddings import Embedder, get_embedder
from app.schemas.chat import ChatRequest, ChatResponse, ToolCallRead
from app.schemas.knowledge_base import SourceRead
from app.services.chat_service import ChatService

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={404: {"description": "Conversation not found (or not yours)"}, 503: {"description": "AI assistant unavailable"}},
)
def chat(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    llm: LLMClient | None = Depends(get_llm),
    embedder: Embedder = Depends(get_embedder),
) -> ChatResponse:
    """Send a message to the AI support agent. It looks up orders and tickets and searches the
    knowledge base with tools, then answers. Returns the answer, its sources and the tools it used."""
    result = ChatService(db, require_llm(llm), embedder).chat(user, conversation_id=body.conversation_id, message=body.message)
    message = result.message
    return ChatResponse(
        conversation_id=result.conversation.id,
        message_id=message.id,
        message=message.content,
        sources=[SourceRead.model_validate(s) for s in message.sources or []],
        tool_calls=[ToolCallRead.model_validate(c) for c in message.tool_calls or []],
        latency_ms=message.latency_ms or 0,
    )
