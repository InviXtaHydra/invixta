"""Import every model here so Alembic and SQLAlchemy see the full schema."""

from app.models.cart import Cart, CartItem
from app.models.conversation import Conversation, Message
from app.models.customer import Customer
from app.models.document import Document, DocumentChunk
from app.models.enums import (
    MessageRole,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    ProductCategory,
    ShippingMethod,
    TicketPriority,
    TicketStatus,
    UserRole,
)
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.product import Product, ProductVariant, Team
from app.models.ticket import SupportTicket
from app.models.user import User

__all__ = [
    "Cart",
    "CartItem",
    "Conversation",
    "Customer",
    "Document",
    "DocumentChunk",
    "Message",
    "MessageRole",
    "Order",
    "OrderItem",
    "OrderStatus",
    "Payment",
    "PaymentMethod",
    "PaymentStatus",
    "Product",
    "ProductCategory",
    "ProductVariant",
    "ShippingMethod",
    "SupportTicket",
    "Team",
    "TicketPriority",
    "TicketStatus",
    "User",
    "UserRole",
]
