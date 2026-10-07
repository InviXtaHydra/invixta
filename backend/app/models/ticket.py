from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import TicketPriority, TicketStatus
from app.models.mixins import TimestampMixin, pg_enum


class SupportTicket(TimestampMixin, Base):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    subject: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[TicketStatus] = mapped_column(pg_enum(TicketStatus, "ticket_status"), default=TicketStatus.OPEN)
    priority: Mapped[TicketPriority] = mapped_column(pg_enum(TicketPriority, "ticket_priority"), default=TicketPriority.MEDIUM)
