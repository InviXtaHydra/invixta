from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import User, UserRole
from app.schemas.metrics import MetricsRead
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/metrics", response_model=MetricsRead)
def metrics(
    days: int = Query(14, ge=1, le=90, description="Length of the daily activity series"),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> MetricsRead:
    """Usage of the AI assistant: conversations, latency, tool calls, RAG searches, tickets and the
    questions it couldn't answer (useful to see which documents are missing)."""
    return MetricsRead.model_validate(MetricsService(db).collect(days))
