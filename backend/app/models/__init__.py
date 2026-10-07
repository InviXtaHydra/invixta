"""Import every model here so Alembic and SQLAlchemy see the full schema."""

from app.models.conversation import Conversation, Message
from app.models.customer import Customer
from app.models.document import Document, DocumentChunk
from app.models.enums import MessageRole, OrderStatus, TicketPriority, TicketStatus, UserRole
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.ticket import SupportTicket
from app.models.user import User

__all__ = [
    "Conversation",
    "Customer",
    "Document",
    "DocumentChunk",
    "Message",
    "MessageRole",
    "Order",
    "OrderItem",
    "OrderStatus",
    "Product",
    "SupportTicket",
    "TicketPriority",
    "TicketStatus",
    "User",
    "UserRole",
]
