from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import TicketStatus, User
from app.schemas.common import Page
from app.schemas.ticket import TicketCreate, TicketRead
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("", response_model=Page[TicketRead])
def list_tickets(
    status: TicketStatus | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[TicketRead]:
    tickets, total = TicketService(db).list_tickets(user, status=status, limit=limit, offset=offset)
    return Page(items=[TicketRead.model_validate(t) for t in tickets], total=total, limit=limit, offset=offset)


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(body: TicketCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> TicketRead:
    ticket = TicketService(db).create_ticket(
        user, subject=body.subject, description=body.description, priority=body.priority, customer_id=body.customer_id
    )
    return TicketRead.model_validate(ticket)


@router.get("/{ticket_id}", response_model=TicketRead, responses={404: {"description": "Ticket not found (or not yours)"}})
def get_ticket(ticket_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> TicketRead:
    return TicketRead.model_validate(TicketService(db).get_ticket(user, ticket_id))
