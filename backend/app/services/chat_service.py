"""Chat: one user message in, one assistant answer out, both stored in the conversation.

A chat turn has two steps, so the streaming endpoint can report "not your conversation" as a normal
HTTP error before it starts streaming:

    start()   checks access, loads (or creates) the conversation and its history
    respond() runs the agent and stores the user message + answer
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.agents.llm import LLMClient
from app.agents.support_agent import AgentEventCallback, AgentResult, SupportAgent
from app.core.config import get_settings
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models import Conversation, Message, MessageRole, User
from app.rag.embeddings import Embedder
from app.repositories.conversation_repository import ConversationRepository
from app.tools.support_tools import SupportTools

logger = logging.getLogger("supportai.chat")


@dataclass
class ChatTurn:
    """A conversation that is ready for the next message."""

    conversation: Conversation
    history: list[dict[str, Any]]
    is_new: bool


@dataclass
class ChatResult:
    conversation: Conversation
    message: Message
    agent: AgentResult


class ChatService:
    def __init__(self, db: Session, llm: LLMClient, embedder: Embedder) -> None:
        self.db = db
        self.llm = llm
        self.embedder = embedder
        self.conversations = ConversationRepository(db)

    def start(self, user: User, conversation_id: int | None) -> ChatTurn:
        if user.customer is None:
            raise PermissionDeniedError("The chat assistant is available to customer accounts")
        if conversation_id is None:
            return ChatTurn(conversation=self.conversations.create(user.customer.id), history=[], is_new=True)

        conversation = self.conversations.get(conversation_id, customer_id=user.customer.id)
        if conversation is None:
            raise NotFoundError(f"Conversation {conversation_id} not found")
        limit = get_settings().chat_history_messages
        history = [{"role": m.role.value, "content": m.content} for m in self.conversations.recent_messages(conversation.id, limit)]
        return ChatTurn(conversation=conversation, history=history, is_new=False)

    def respond(self, user: User, turn: ChatTurn, message: str, on_event: AgentEventCallback | None = None) -> ChatResult:
        settings = get_settings()
        started = time.perf_counter()
        agent = SupportAgent(self.llm, SupportTools(self.db, user, self.embedder), user, settings.agent_max_tool_rounds)
        # If the LLM fails this raises before anything is written; the request's session is discarded.
        result = agent.run(turn.history, message, on_event=on_event)
        latency_ms = round((time.perf_counter() - started) * 1000)

        conversation = turn.conversation
        self.conversations.add_message(conversation, MessageRole.USER, message)
        reply = self.conversations.add_message(
            conversation,
            MessageRole.ASSISTANT,
            result.text,
            tool_calls=[c.as_dict() for c in result.tool_calls],
            sources=[s.as_source() for s in result.sources],
            latency_ms=latency_ms,
        )
        self.db.commit()
        logger.info(
            "chat turn",
            extra={
                "conversation_id": conversation.id,
                "latency_ms": latency_ms,
                "tool_calls": len(result.tool_calls),
                "sources": len(result.sources),
            },
        )
        return ChatResult(conversation=conversation, message=reply, agent=result)

    def chat(self, user: User, *, conversation_id: int | None, message: str) -> ChatResult:
        """Both steps in one call (the non-streaming POST /chat)."""
        return self.respond(user, self.start(user, conversation_id), message)
