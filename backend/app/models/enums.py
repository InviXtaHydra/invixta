"""Enumerations stored as native PostgreSQL enum types."""

import enum


class UserRole(enum.StrEnum):
    CUSTOMER = "CUSTOMER"
    AGENT = "AGENT"  # human support agent
    ADMIN = "ADMIN"


class OrderStatus(enum.StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class TicketStatus(enum.StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class MessageRole(enum.StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ProductCategory(enum.StrEnum):
    HOME = "home"  # home shirt of the current season
    AWAY = "away"
    RETRO = "retro"  # remake of a classic shirt
    TRAINING = "training"
    KIDS = "kids"
    ACCESSORY = "accessory"  # scarves, socks, balls


class ShippingMethod(enum.StrEnum):
    STANDARD = "standard"
    EXPRESS = "express"


class PaymentMethod(enum.StrEnum):
    IDEAL = "ideal"
    BANCONTACT = "bancontact"
    CARD = "card"
    PAYPAL = "paypal"


class PaymentStatus(enum.StrEnum):
    PENDING = "pending"  # waiting for the customer on the payment page
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
