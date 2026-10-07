"""Tools the support agent can call. Each tool reuses the same services as the REST API, so the agent
gets exactly the same authorization rules: a customer can never read another customer's data,
whatever the model asks for.

A tool returns JSON for the model plus a short human-readable summary for the chat UI.
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models import Order, OrderStatus, TicketPriority, TicketStatus, User
from app.rag.embeddings import Embedder
from app.rag.retrieval import KnowledgeBaseSearch, RetrievedChunk
from app.services.access import is_staff
from app.services.order_service import OrderService
from app.services.ticket_service import TicketService

logger = logging.getLogger("supportai.tools")

# --- Tool definitions sent to the model (JSON Schema) -----------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "get_order_status",
        "description": (
            "Look up one order by its order number: status, carrier, tracking number, estimated delivery and items. "
            "Use this whenever the customer asks about a specific order."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "The order number, e.g. '10482' or '#10482'"}},
            "required": ["order_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_customer_orders",
        "description": (
            "List the customer's orders, newest first. Use this when the customer doesn't give an order number "
            "(e.g. 'where is my order?') or asks about their orders in general."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer", "description": "Leave out to use the signed-in customer"},
                "status": {"type": "string", "enum": [s.value for s in OrderStatus], "description": "Only orders with this status"},
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_knowledge_base",
        "description": (
            "Search the company's policy documents (returns, shipping, warranty, payments, product information). "
            "Use this for ANY question about company policies or products, and only answer from what it returns."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "A short, self-contained search question"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_support_ticket",
        "description": (
            "Open a support ticket for a problem a human needs to handle (damaged or wrong item, lost parcel, refund "
            "issue, warranty claim). Collect the order number and a clear description first. Returns the ticket ID."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Short summary, 3-200 characters"},
                "description": {"type": "string", "description": "What happened, in the customer's words, at least 10 characters"},
                "priority": {"type": "string", "enum": [p.value for p in TicketPriority]},
                "order_id": {"type": "string", "description": "Related order number, if any"},
                "customer_id": {"type": "integer", "description": "Leave out to use the signed-in customer"},
            },
            "required": ["subject", "description", "priority"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_support_tickets",
        "description": "List the customer's support tickets with their status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer", "description": "Leave out to use the signed-in customer"},
                "status": {"type": "string", "enum": [s.value for s in TicketStatus]},
            },
            "required": [],
            "additionalProperties": False,
        },
    },
]

# --- Argument validation (the model's JSON is checked like any other user input) ---------------


class OrderStatusArgs(BaseModel):
    order_id: str = Field(min_length=1, max_length=20)


class CustomerOrdersArgs(BaseModel):
    customer_id: int | None = None
    status: OrderStatus | None = None


class SearchArgs(BaseModel):
    query: str = Field(min_length=3, max_length=500)


class CreateTicketArgs(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    priority: TicketPriority = TicketPriority.MEDIUM
    order_id: str | None = Field(default=None, max_length=20)
    customer_id: int | None = None


class TicketsArgs(BaseModel):
    customer_id: int | None = None
    status: TicketStatus | None = None


@dataclass
class ToolResult:
    content: str  # JSON sent back to the model
    is_error: bool
    summary: str  # shown in the chat UI, e.g. "Order #10012: shipped"
    sources: list[RetrievedChunk] = field(default_factory=list)


class ToolError(Exception):
    """A problem the model should hear about (and can explain to the customer)."""


def parse_order_number(value: str) -> int:
    digits = re.sub(r"[^\d]", "", value)
    if not digits or len(digits) > 9:
        raise ToolError(f"'{value}' is not a valid order number")
    return int(digits)


class SupportTools:
    """Executes tool calls on behalf of one signed-in user."""

    def __init__(self, db: Session, user: User, embedder: Embedder) -> None:
        self.db = db
        self.user = user
        self.orders = OrderService(db)
        self.tickets = TicketService(db)
        self.kb = KnowledgeBaseSearch(db, embedder)
        self.source_counter = 0  # numbering of knowledge-base sources within one answer: [S1], [S2], …

    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        started = time.perf_counter()
        handler = getattr(self, f"_tool_{name}", None)
        try:
            if handler is None or name not in {t["name"] for t in TOOL_DEFINITIONS}:
                raise ToolError(f"Unknown tool '{name}'")
            result: ToolResult = handler(arguments)
        except ValidationError as exc:
            message = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
            result = ToolResult(content=json.dumps({"error": f"Invalid arguments: {message}"}), is_error=True, summary="Invalid request")
        except (ToolError, AppError) as exc:
            detail = exc.detail if isinstance(exc, AppError) else str(exc)
            result = ToolResult(content=json.dumps({"error": detail}), is_error=True, summary=detail)
        logger.info(
            "tool call",
            extra={
                "tool": name,
                "ok": not result.is_error,
                "duration_ms": round((time.perf_counter() - started) * 1000),
                # Argument names only (values can contain personal details), except the order number.
                "argument_names": sorted(arguments),
                "order_id": arguments.get("order_id"),
            },
        )
        return result

    # --- Scope helper -----------------------------------------------------------------------------

    def _check_customer(self, customer_id: int | None) -> None:
        """Customers may only name their own customer_id; staff may name anyone."""
        if customer_id is None or is_staff(self.user):
            return
        own = self.user.customer.id if self.user.customer else None
        if customer_id != own:
            raise ToolError("You can only access the signed-in customer's own account")

    # --- Tools ----------------------------------------------------------------------------------

    def _tool_get_order_status(self, arguments: dict[str, Any]) -> ToolResult:
        args = OrderStatusArgs.model_validate(arguments)
        order = self.orders.get_order(self.user, parse_order_number(args.order_id))
        data = _order_json(order, with_items=True)
        return ToolResult(content=json.dumps(data), is_error=False, summary=f"Order #{order.id}: {order.status.value}")

    def _tool_get_customer_orders(self, arguments: dict[str, Any]) -> ToolResult:
        args = CustomerOrdersArgs.model_validate(arguments)
        self._check_customer(args.customer_id)
        orders, total = self.orders.list_orders(self.user, customer_id=args.customer_id, status=args.status, limit=10, offset=0)
        data = {"total": total, "orders": [_order_json(o, with_items=False) for o in orders]}
        return ToolResult(content=json.dumps(data), is_error=False, summary=f"{len(orders)} order(s) found")

    def _tool_search_knowledge_base(self, arguments: dict[str, Any]) -> ToolResult:
        args = SearchArgs.model_validate(arguments)
        chunks = self.kb.search(args.query)
        if not chunks:
            data: dict[str, Any] = {"results": [], "note": "Nothing relevant found in the knowledge base."}
            return ToolResult(content=json.dumps(data), is_error=False, summary="No relevant documents")
        results = []
        for chunk in chunks:
            self.source_counter += 1
            results.append(
                {"source": f"S{self.source_counter}", "document": chunk.filename, "page": chunk.page_number, "text": chunk.content}
            )
        names = ", ".join(sorted({c.filename for c in chunks}))
        return ToolResult(content=json.dumps({"results": results}), is_error=False, summary=f"Found in {names}", sources=chunks)

    def _tool_create_support_ticket(self, arguments: dict[str, Any]) -> ToolResult:
        args = CreateTicketArgs.model_validate(arguments)
        self._check_customer(args.customer_id)
        description = args.description
        if args.order_id:
            order = self.orders.get_order(self.user, parse_order_number(args.order_id))  # must be their own order
            description = f"Order #{order.id}: {description}"
        ticket = self.tickets.create_ticket(
            self.user, subject=args.subject, description=description, priority=args.priority, customer_id=args.customer_id
        )
        data = {"ticket_id": ticket.id, "status": ticket.status.value, "priority": ticket.priority.value, "subject": ticket.subject}
        return ToolResult(content=json.dumps(data), is_error=False, summary=f"Ticket #{ticket.id} created")

    def _tool_get_support_tickets(self, arguments: dict[str, Any]) -> ToolResult:
        args = TicketsArgs.model_validate(arguments)
        self._check_customer(args.customer_id)
        tickets, total = self.tickets.list_tickets(self.user, customer_id=args.customer_id, status=args.status, limit=10, offset=0)
        data = {
            "total": total,
            "tickets": [
                {
                    "ticket_id": t.id,
                    "subject": t.subject,
                    "status": t.status.value,
                    "priority": t.priority.value,
                    "created_at": t.created_at.date().isoformat(),
                }
                for t in tickets
            ],
        }
        return ToolResult(content=json.dumps(data), is_error=False, summary=f"{len(tickets)} ticket(s) found")


def _order_json(order: Order, *, with_items: bool) -> dict[str, Any]:
    data: dict[str, Any] = {
        "order_id": order.id,
        "status": order.status.value,
        "ordered_on": order.created_at.date().isoformat(),
        "last_update": order.updated_at.date().isoformat(),
        "total_amount_eur": str(order.total_amount),
        "carrier": order.carrier,
        "tracking_number": order.tracking_number,
        "estimated_delivery": order.estimated_delivery.isoformat() if order.estimated_delivery else None,
    }
    if with_items:
        data["items"] = [{"product": i.product.name, "quantity": i.quantity, "unit_price_eur": str(i.price)} for i in order.items]
    return data
