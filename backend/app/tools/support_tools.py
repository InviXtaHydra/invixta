"""Tools the support agent can call. Each tool reuses the same services as the REST API, so the agent
gets exactly the same authorization rules: a customer can never read another customer's data,
whatever the model asks for.

The tools have no customer_id argument: they always work on the signed-in customer. The model can't
even name another customer (an earlier version accepted customer_id; a small local model then made
up ids, which were refused, so its ticket never got created). Unknown arguments are rejected.

A tool returns JSON for the model plus a short human-readable summary for the chat UI.
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models import Order, OrderStatus, ProductCategory, TicketPriority, TicketStatus, User
from app.rag.embeddings import Embedder
from app.rag.retrieval import KnowledgeBaseSearch, RetrievedChunk
from app.repositories.catalog_repository import CatalogRepository, ProductFilters
from app.services.order_service import OrderService
from app.services.ticket_service import TicketService

logger = logging.getLogger("supportai.tools")

# Generic words in club names, ignored when looking for a club in a message ("FC", "United", …).
CLUB_WORDS = {"fc", "sv", "sc", "real", "sporting", "atlético", "atletico", "united", "city", "rovers", "athletic", "1908"}

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
            "List the signed-in customer's orders, newest first. Use this when the customer doesn't give an order number "
            "(e.g. 'where is my order?') or asks about their orders in general."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
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
            },
            "required": ["subject", "description", "priority"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_products",
        "description": (
            "Search the shop's products: shirts (home, away, retro, training, kids) and accessories of the clubs we sell. "
            "Returns names, prices, sale prices and the sizes in stock. Use it when the customer asks whether something "
            "is available, in stock in a size, or what it costs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Club, product or kind of item, e.g. 'Polder United home shirt'"},
                "size": {"type": "string", "description": "Only products with this size in stock, e.g. 'M' or '140'"},
                "category": {"type": "string", "enum": [c.value for c in ProductCategory]},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "request_order_cancellation",
        "description": (
            "Check whether one of the customer's orders can still be cancelled (only before it ships) and offer the "
            "customer a confirmation button in the chat. This does NOT cancel the order: the customer confirms it "
            "themselves. Use it when the customer asks to cancel an order."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "The order number"}},
            "required": ["order_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_support_tickets",
        "description": "List the customer's support tickets with their status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": [s.value for s in TicketStatus]},
            },
            "required": [],
            "additionalProperties": False,
        },
    },
]

# --- Argument validation (the model's JSON is checked like any other user input) ---------------


class ToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")  # e.g. a made-up customer_id is an error the model hears about


class OrderStatusArgs(ToolArgs):
    order_id: str = Field(min_length=1, max_length=20)


class CustomerOrdersArgs(ToolArgs):
    status: OrderStatus | None = None


class SearchArgs(ToolArgs):
    query: str = Field(min_length=3, max_length=500)


class ProductSearchArgs(ToolArgs):
    query: str = Field(min_length=2, max_length=100)
    size: str | None = Field(default=None, max_length=12)
    category: ProductCategory | None = None


class CancellationArgs(ToolArgs):
    order_id: str = Field(min_length=1, max_length=20)


class CreateTicketArgs(ToolArgs):
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    priority: TicketPriority = TicketPriority.MEDIUM
    order_id: str | None = Field(default=None, max_length=20)


class TicketsArgs(ToolArgs):
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

    def mentioned_teams(self, message: str) -> list[str]:
        """Names of the clubs a message mentions, also by their core name ("Polder" for Polder United)."""
        text = message.lower()
        found = []
        for team in CatalogRepository(self.db).teams():
            core = [w for w in team.name.lower().split() if w not in CLUB_WORDS]
            if team.name.lower() in text or any(len(w) > 3 and w in text for w in [*core, team.city.lower()]):
                found.append(team.name)
        return found

    # --- Tools ----------------------------------------------------------------------------------

    def _tool_get_order_status(self, arguments: dict[str, Any]) -> ToolResult:
        args = OrderStatusArgs.model_validate(arguments)
        order = self.orders.get_order(self.user, parse_order_number(args.order_id))
        data = _order_json(order, with_items=True)
        return ToolResult(content=json.dumps(data), is_error=False, summary=f"Order #{order.id}: {order.status.value}")

    def _tool_get_customer_orders(self, arguments: dict[str, Any]) -> ToolResult:
        args = CustomerOrdersArgs.model_validate(arguments)
        orders, total = self.orders.list_orders(self.user, status=args.status, limit=10, offset=0)
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

    def _tool_search_products(self, arguments: dict[str, Any]) -> ToolResult:
        args = ProductSearchArgs.model_validate(arguments)
        catalog = CatalogRepository(self.db)
        filters = ProductFilters(category=args.category, size=args.size.upper() if args.size else None, q=args.query)
        products = catalog.list(filters, "popular", limit=6, offset=0)
        if not products and len(args.query.split()) > 1:
            # "Polder United home shirt" → try the club or product name on its own words
            filters.q = " ".join(w for w in args.query.split() if w.lower() not in {"shirt", "shirts", "kit", "the", "a"})
            products = catalog.list(filters, "popular", limit=6, offset=0) if filters.q else []
        results = [
            {
                "product": p.name,
                "club": p.team.name if p.team else None,
                "price_eur": str(p.price),
                **({"was_eur": str(p.compare_at_price)} if p.compare_at_price else {}),
                "sizes_in_stock": [v.size for v in p.variants if v.stock > 0],
                "name_and_number_printing": p.personalizable,
                "link": f"/product/{p.slug}",
            }
            for p in products
        ]
        data: dict[str, Any] = {"results": results} if results else {"results": [], "note": "No products match."}
        size_note = f" in size {args.size.upper()}" if args.size else ""
        summary = f"{len(results)} product(s) found{size_note}" if results else f"No products found{size_note}"
        return ToolResult(content=json.dumps(data), is_error=False, summary=summary)

    def _tool_request_order_cancellation(self, arguments: dict[str, Any]) -> ToolResult:
        """Human in the loop: the agent can only *offer* a cancellation; the customer confirms it in the chat."""
        args = CancellationArgs.model_validate(arguments)
        order = self.orders.get_order(self.user, parse_order_number(args.order_id))
        if order.status not in (OrderStatus.PENDING, OrderStatus.PROCESSING):
            raise ToolError(f"Order #{order.id} is {order.status.value} and can't be cancelled anymore")
        data = {
            "order_id": order.id,
            "can_cancel": True,
            "total_amount_eur": str(order.total_amount),
            "refund": "a paid order is refunded straight away" if order.payment_status.value == "paid" else "nothing was paid yet",
            "next_step": "A 'Cancel order' button appears below your reply in this chat. The order is NOT cancelled until "
            "the customer presses it.",
        }
        return ToolResult(
            content=json.dumps(data), is_error=False, summary=f"Order #{order.id} can be cancelled: waiting for your confirmation"
        )

    def _tool_create_support_ticket(self, arguments: dict[str, Any]) -> ToolResult:
        args = CreateTicketArgs.model_validate(arguments)
        description = args.description
        if args.order_id:
            order = self.orders.get_order(self.user, parse_order_number(args.order_id))  # must be their own order
            description = f"Order #{order.id}: {description}"
        ticket = self.tickets.create_ticket(self.user, subject=args.subject, description=description, priority=args.priority)
        data = {"ticket_id": ticket.id, "status": ticket.status.value, "priority": ticket.priority.value, "subject": ticket.subject}
        return ToolResult(content=json.dumps(data), is_error=False, summary=f"Ticket #{ticket.id} created")

    def _tool_get_support_tickets(self, arguments: dict[str, Any]) -> ToolResult:
        args = TicketsArgs.model_validate(arguments)
        tickets, total = self.tickets.list_tickets(self.user, status=args.status, limit=10, offset=0)
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
        "payment_status": order.payment_status.value,
        "ordered_on": order.created_at.date().isoformat(),
        "last_update": order.updated_at.date().isoformat(),
        "total_amount_eur": str(order.total_amount),
        "shipping_cost_eur": str(order.shipping_cost),
        "shipping_method": order.shipping_method.value,
        "ships_to": f"{order.shipping_city}, {order.shipping_country}" if order.shipping_city else None,
        "carrier": order.carrier,
        "tracking_number": order.tracking_number,
        "estimated_delivery": order.estimated_delivery.isoformat() if order.estimated_delivery else None,
        "can_still_be_cancelled": order.status in (OrderStatus.PENDING, OrderStatus.PROCESSING),
    }
    if with_items:
        data["items"] = [
            {
                "product": i.product_name or i.product.name,
                "size": i.size,
                "quantity": i.quantity,
                "unit_price_eur": str(i.price),
                **({"printed_name": i.personalization_name} if i.personalization_name else {}),
                **({"printed_number": i.personalization_number} if i.personalization_number is not None else {}),
            }
            for i in order.items
        ]
    return data
