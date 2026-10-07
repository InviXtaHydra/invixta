from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import SupportTicket, TicketPriority, TicketStatus


class TicketRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, *, customer_id: int | None, status: TicketStatus | None = None, limit: int = 20, offset: int = 0) -> list[SupportTicket]:
        query = select(SupportTicket).order_by(SupportTicket.created_at.desc(), SupportTicket.id.desc())
        if customer_id is not None:
            query = query.where(SupportTicket.customer_id == customer_id)
        if status is not None:
            query = query.where(SupportTicket.status == status)
        return list(self.db.scalars(query.limit(limit).offset(offset)))

    def count(self, *, customer_id: int | None, status: TicketStatus | None = None) -> int:
        query = select(func.count()).select_from(SupportTicket)
        if customer_id is not None:
            query = query.where(SupportTicket.customer_id == customer_id)
        if status is not None:
            query = query.where(SupportTicket.status == status)
        return self.db.scalar(query) or 0

    def get(self, ticket_id: int, *, customer_id: int | None) -> SupportTicket | None:
        query = select(SupportTicket).where(SupportTicket.id == ticket_id)
        if customer_id is not None:
            query = query.where(SupportTicket.customer_id == customer_id)
        return self.db.scalar(query)

    def create(self, *, customer_id: int, subject: str, description: str, priority: TicketPriority) -> SupportTicket:
        ticket = SupportTicket(customer_id=customer_id, subject=subject, description=description, priority=priority, status=TicketStatus.OPEN)
        self.db.add(ticket)
        self.db.flush()
        return ticket
