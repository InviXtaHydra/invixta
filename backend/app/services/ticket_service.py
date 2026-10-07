from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models import SupportTicket, TicketPriority, TicketStatus, User
from app.repositories.customer_repository import CustomerRepository
from app.repositories.ticket_repository import TicketRepository
from app.services.access import customer_scope, is_staff, scope_for


class TicketService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.tickets = TicketRepository(db)
        self.customers = CustomerRepository(db)

    def list_tickets(
        self, user: User, *, customer_id: int | None = None, status: TicketStatus | None, limit: int, offset: int
    ) -> tuple[list[SupportTicket], int]:
        scope = scope_for(user, customer_id)
        return (
            self.tickets.list(customer_id=scope, status=status, limit=limit, offset=offset),
            self.tickets.count(customer_id=scope, status=status),
        )

    def get_ticket(self, user: User, ticket_id: int) -> SupportTicket:
        ticket = self.tickets.get(ticket_id, customer_id=customer_scope(user))
        if ticket is None:
            raise NotFoundError(f"Ticket {ticket_id} not found")
        return ticket

    def create_ticket(
        self, user: User, *, subject: str, description: str, priority: TicketPriority, customer_id: int | None = None
    ) -> SupportTicket:
        """Customers open tickets for themselves; staff open tickets on behalf of a given customer."""
        if is_staff(user):
            if customer_id is None:
                raise PermissionDeniedError("Staff must specify customer_id when creating a ticket")
            if not self.customers.exists(customer_id):
                raise NotFoundError(f"Customer {customer_id} not found")
            target = customer_id
        else:
            if user.customer is None:
                raise PermissionDeniedError("This account has no customer profile")
            if customer_id is not None and customer_id != user.customer.id:
                raise PermissionDeniedError("You can only open tickets for your own account")
            target = user.customer.id
        ticket = self.tickets.create(customer_id=target, subject=subject, description=description, priority=priority)
        self.db.commit()
        return ticket

    def update_ticket(self, user: User, ticket_id: int, *, status: TicketStatus | None, priority: TicketPriority | None) -> SupportTicket:
        if not is_staff(user):
            raise PermissionDeniedError("Only support staff can change a ticket's status or priority")
        ticket = self.get_ticket(user, ticket_id)
        if status is not None:
            ticket.status = status
        if priority is not None:
            ticket.priority = priority
        self.db.commit()
        self.db.refresh(ticket)  # updated_at is set by the database
        return ticket
