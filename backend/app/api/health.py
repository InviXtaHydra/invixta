from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agents.llm import LLMClient, get_llm
from app.core.database import get_db
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db), llm: LLMClient = Depends(get_llm)) -> HealthResponse:
    """Liveness + database check, plus whether the AI model is ready.

    The API stays healthy when Ollama is down (orders, tickets and search still work); `llm` tells you why
    the chat can't answer."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - only when the database is down
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Database unavailable") from exc
    check = getattr(llm, "status", None)  # OllamaClient asks Ollama; the scripted test model has no server
    llm_status = str(check()) if callable(check) else "scripted"
    return HealthResponse(status="ok", database="ok", llm=llm_status, llm_model=llm.model)
