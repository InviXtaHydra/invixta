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
