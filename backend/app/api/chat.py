"""Chat endpoints: POST /chat returns the whole answer at once, POST /chat/stream streams it (SSE)."""

import contextvars
import json
import logging
import queue
import threading
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agents.llm import LLMClient, get_llm
from app.core.database import SessionFactory, get_db, get_session_factory
from app.core.deps import get_current_user
from app.core.exceptions import AppError
from app.core.rate_limit import chat_limiter
from app.models import User
from app.rag.embeddings import Embedder, get_embedder
from app.schemas.chat import ChatRequest, ChatResponse, ToolCallRead
from app.schemas.knowledge_base import SourceRead
from app.services.chat_service import ChatResult, ChatService

router = APIRouter(tags=["chat"])
logger = logging.getLogger("invixta.chat")

ERRORS: dict[int | str, dict[str, Any]] = {
    403: {"description": "Only customer accounts can chat"},
    404: {"description": "Conversation not found (or not yours)"},
    429: {"description": "Too many messages per minute"},
    503: {"description": "The AI model (Ollama) isn't reachable"},
}


def to_response(result: ChatResult) -> ChatResponse:
    message = result.message
    return ChatResponse(
        conversation_id=result.conversation.id,
        message_id=message.id,
        message=message.content,
        sources=[SourceRead.model_validate(s) for s in message.sources or []],
        tool_calls=[ToolCallRead.model_validate(c) for c in message.tool_calls or []],
        latency_ms=message.latency_ms or 0,
    )


@router.post("/chat", response_model=ChatResponse, responses=ERRORS)
def chat(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm),
    embedder: Embedder = Depends(get_embedder),
) -> ChatResponse:
    """Send a message to the AI support agent. It looks up orders and tickets and searches the
    knowledge base with tools, then answers. Returns the answer, its sources and the tools it used."""
    chat_limiter().hit(f"user:{user.id}")
    return to_response(ChatService(db, llm, embedder).chat(user, conversation_id=body.conversation_id, message=body.message))


def sse(event: dict[str, Any]) -> str:
    """One Server-Sent Event: a `data:` line with JSON, then a blank line."""
    return f"data: {json.dumps(event, default=str)}\n\n"


@router.post(
    "/chat/stream",
    responses={**ERRORS, 200: {"description": "text/event-stream of JSON events", "content": {"text/event-stream": {}}}},
)
def chat_stream(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm),
    embedder: Embedder = Depends(get_embedder),
    session_factory: SessionFactory = Depends(get_session_factory),
) -> StreamingResponse:
    """Like POST /chat, but streams progress as Server-Sent Events, one JSON object per event:

    - `{"type": "start", "conversation_id": 12}`
    - `{"type": "tool_start", "name": "get_order_status", "arguments": {...}}`
    - `{"type": "tool_end", "name": ..., "status": "ok", "summary": "Order #10012: shipped", "duration_ms": 8}`
    - `{"type": "text", "delta": "Your order "}`, repeated while the answer is written
    - `{"type": "done", ...}` with the same fields as the POST /chat response, or `{"type": "error", "detail": ...}`

    Access checks happen before the stream starts, so they still return normal 403/404/429 responses.
    If the model fails while answering (e.g. Ollama isn't running), the stream ends with an error event.
    """
    chat_limiter().hit(f"user:{user.id}")
    ChatService(db, llm, embedder).check_access(user, body.conversation_id)
    user_id = user.id
    events: queue.Queue[dict[str, Any] | None] = queue.Queue()

    def work() -> None:
        # Runs in a worker thread with its own database session: if the customer closes the page
        # mid-answer, the request's session is closed, but the agent still finishes and saves the answer.
        with session_factory() as worker_db:
            try:
                worker_user = worker_db.get(User, user_id)
                assert worker_user is not None
                service = ChatService(worker_db, llm, embedder)
                turn = service.start(worker_user, body.conversation_id)
                events.put({"type": "start", "conversation_id": turn.conversation.id})
                result = service.respond(worker_user, turn, body.message, on_event=events.put)
                events.put({"type": "done", **to_response(result).model_dump(mode="json")})
            except AppError as exc:
                worker_db.rollback()
                logger.warning("chat stream failed", extra={"status": exc.status_code, "error": type(exc).__name__})
                events.put({"type": "error", "detail": exc.detail})
            except Exception:
                worker_db.rollback()
                logger.exception("chat stream failed")
                events.put({"type": "error", "detail": "Something went wrong while answering. Please try again."})
            finally:
                events.put(None)  # end of stream

    def stream() -> Iterator[str]:
        # copy_context(): the worker keeps this request's id in its log lines.
        threading.Thread(target=contextvars.copy_context().run, args=(work,), daemon=True).start()
        while (event := events.get()) is not None:
            yield sse(event)

    # X-Accel-Buffering: tell nginx not to buffer, so events reach the browser immediately.
    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(stream(), media_type="text/event-stream", headers=headers)
