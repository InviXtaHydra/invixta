"""Fill the database with realistic demo data.

Run inside the backend container:
    docker compose exec backend python scripts/seed_database.py          # only if the database is empty
    docker compose exec backend python scripts/seed_database.py --reset  # wipe and re-seed

All demo accounts use the password printed at the end. Never run --reset against real data.
"""

import argparse
import random
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Make `import app` work when the script is run from /app/scripts.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import (
    Conversation,
    Customer,
    Message,
    MessageRole,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    SupportTicket,
    TicketPriority,
    TicketStatus,
    User,
    UserRole,
)

DEMO_PASSWORD = "Password123!"

STAFF = [
    ("admin@supportai.dev", UserRole.ADMIN),
    ("agent@supportai.dev", UserRole.AGENT),
]

CUSTOMERS = [
    ("Emma de Vries", "emma.devries@example.com"),
    ("Lucas Janssens", "lucas.janssens@example.com"),
    ("Sofia Martens", "sofia.martens@example.com"),
    ("Noah Peeters", "noah.peeters@example.com"),
    ("Mila Claes", "mila.claes@example.com"),
]

PRODUCTS = [
    ("Aurora Wireless Headphones", "Over-ear Bluetooth headphones with active noise cancelling and 30-hour battery life.", "149.99", 42),
    ("Nordic Ceramic Mug Set", "Set of four hand-glazed stoneware mugs, 350 ml, dishwasher safe.", "34.95", 120),
    ("TrailPro Hiking Backpack 28L", "Water-resistant daypack with hip belt, laptop sleeve and rain cover.", "89.00", 35),
    ("Lumen Smart Desk Lamp", "Dimmable LED desk lamp with USB-C charging port and colour temperature control.", "59.90", 64),
    ("Barista Pour-Over Kettle", "1 L gooseneck kettle with built-in thermometer, stainless steel.", "44.50", 27),
    ("FlexFit Yoga Mat", "6 mm non-slip natural rubber mat with carrying strap.", "39.99", 80),
    ("Pixel Mechanical Keyboard", "Compact 75% wireless mechanical keyboard with hot-swappable switches.", "119.00", 18),
    ("Terra Linen Bed Sheet Set", "Stonewashed linen double-bed sheet set: fitted sheet, flat sheet and two pillowcases.", "129.00", 22),
    ("Volt 20,000 mAh Power Bank", "USB-C PD 65 W power bank, charges a laptop and a phone at the same time.", "54.99", 95),
    ("Cedar Wood Cutting Board", "End-grain cedar cutting board, 40 x 28 cm, with juice groove.", "64.00", 15),
]

CARRIERS = ["PostNL", "DHL", "bpost", "UPS", "DPD"]

# How many days ago the 20 orders were placed. Their status follows from their age (see _status_for_age),
# like in a real shop: recent orders are still open, older ones are delivered (or cancelled).
ORDER_AGES_DAYS = [0, 1, 2, 3, 4, 5, 6, 8, 9, 11, 13, 16, 21, 27, 34, 41, 48, 57, 66, 83]

TICKETS = [
    # (customer index, subject, description, status, priority)
    (
        0,
        "Parcel arrived damaged",
        "The box was crushed and one of the Nordic mugs is cracked. I have photos of the packaging.",
        TicketStatus.OPEN,
        TicketPriority.HIGH,
    ),
    (
        0,
        "Change delivery address",
        "Can you deliver my processing order to my office address instead? It's in the same city.",
        TicketStatus.RESOLVED,
        TicketPriority.MEDIUM,
    ),
    (
        1,
        "Headphones won't pair",
        "The Aurora headphones don't show up in my phone's Bluetooth list after a reset.",
        TicketStatus.IN_PROGRESS,
        TicketPriority.MEDIUM,
    ),
    (
        1,
        "Invoice with VAT number",
        "I need an invoice with my company VAT number for my last order.",
        TicketStatus.CLOSED,
        TicketPriority.LOW,
    ),
    (
        2,
        "Tracking hasn't updated",
        "My tracking number has shown 'in transit' for five days without any update.",
        TicketStatus.OPEN,
        TicketPriority.MEDIUM,
    ),
    (
        3,
        "Refund not received",
        "I cancelled my order two weeks ago but haven't received the refund yet.",
        TicketStatus.IN_PROGRESS,
        TicketPriority.URGENT,
    ),
    (3, "Wrong colour keyboard", "I ordered the keyboard in white but received the black version.", TicketStatus.OPEN, TicketPriority.HIGH),
    (
        4,
        "Question about warranty",
        "How long is the warranty on the smart desk lamp, and does it cover the LED?",
        TicketStatus.RESOLVED,
        TicketPriority.LOW,
    ),
]

CONVERSATIONS = [
    (
        0,
        [
            (MessageRole.USER, "Hi, where is my latest order?"),
            (MessageRole.ASSISTANT, "Let me check that for you. Your most recent order has shipped and is on its way."),
        ],
    ),
    (2, [(MessageRole.USER, "What is your return policy?"), (MessageRole.ASSISTANT, "I'll look that up in our policy documents.")]),
]


def reset(db: Session) -> None:
    tables = "messages, conversations, support_tickets, order_items, orders, products, customers, users, document_chunks, documents"
    db.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    # RESTART IDENTITY resets order numbers to the column's START value (10001).
    db.commit()


def seed(db: Session) -> dict[str, int]:
    rng = random.Random(42)  # deterministic: the same data on every run
    now = datetime.now(UTC)
    password_hash = hash_password(DEMO_PASSWORD)  # hashed once; bcrypt is deliberately slow

    for email, role in STAFF:
        db.add(User(email=email, password_hash=password_hash, role=role))

    customers: list[Customer] = []
    for i, (name, email) in enumerate(CUSTOMERS):
        user = User(email=email, password_hash=password_hash, role=UserRole.CUSTOMER, created_at=now - timedelta(days=200 - i * 20))
        user.customer = Customer(name=name, email=email, created_at=user.created_at)
        db.add(user)
        customers.append(user.customer)

    products = [Product(name=n, description=d, price=Decimal(p), stock=s) for n, d, p, s in PRODUCTS]
    db.add_all(products)
    db.flush()

    # Oldest first, so order numbers (10001, 10002, …) increase with the order date.
    orders: list[Order] = []
    for age in sorted(ORDER_AGES_DAYS, reverse=True):
        created_at = now - timedelta(days=age, hours=rng.randint(0, 20))
        order = Order(
            customer_id=rng.choice(customers).id, status=_status_for_age(age, rng), total_amount=Decimal("0"), created_at=created_at
        )
        for product in rng.sample(products, k=rng.randint(1, 3)):
            order.items.append(OrderItem(product_id=product.id, quantity=rng.randint(1, 2), price=product.price))
        order.total_amount = sum((i.price * i.quantity for i in order.items), Decimal("0"))
        _set_shipping(order, age, rng, now)
        orders.append(order)
    db.add_all(orders)

    for idx, subject, description, status, priority in TICKETS:
        created = now - timedelta(days=rng.randint(1, 30))
        db.add(
            SupportTicket(
                customer_id=customers[idx].id,
                subject=subject,
                description=description,
                status=status,
                priority=priority,
                created_at=created,
                updated_at=created,
            )
        )

    for idx, messages in CONVERSATIONS:
        conv = Conversation(customer_id=customers[idx].id)
        for message_role, content in messages:
            conv.messages.append(Message(role=message_role, content=content))
        db.add(conv)

    db.commit()
    return {
        "users": db.scalar(select(func.count()).select_from(User)) or 0,
        "customers": len(customers),
        "products": len(products),
        "orders": len(orders),
        "order_items": sum(len(o.items) for o in orders),
        "tickets": len(TICKETS),
        "conversations": len(CONVERSATIONS),
    }


def _status_for_age(age_days: int, rng: random.Random) -> OrderStatus:
    if age_days <= 1:
        return OrderStatus.PENDING if age_days == 0 else OrderStatus.PROCESSING
    if age_days <= 4:
        return OrderStatus.PROCESSING if age_days <= 2 else OrderStatus.SHIPPED
    if age_days <= 9:
        return OrderStatus.SHIPPED
    return OrderStatus.CANCELLED if rng.random() < 0.15 else OrderStatus.DELIVERED


def _set_shipping(order: Order, age_days: int, rng: random.Random, now: datetime) -> None:
    """Fill carrier, tracking number, estimated delivery and updated_at consistently with the status."""
    created = order.created_at
    if order.status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
        order.carrier = rng.choice(CARRIERS)
        order.tracking_number = f"{order.carrier[:2].upper()}{rng.randint(10**9, 10**10 - 1)}"

    if order.status == OrderStatus.PENDING:
        order.estimated_delivery = (now + timedelta(days=rng.randint(4, 6))).date()
        order.updated_at = created
    elif order.status == OrderStatus.PROCESSING:
        order.estimated_delivery = (now + timedelta(days=rng.randint(2, 4))).date()
        order.updated_at = created + timedelta(hours=rng.randint(2, 20))
    elif order.status == OrderStatus.SHIPPED:
        shipped_at = created + timedelta(days=min(2, age_days), hours=rng.randint(1, 8))
        # Still in transit: the estimate is today or later.
        order.estimated_delivery = max(now.date(), (shipped_at + timedelta(days=rng.randint(2, 5))).date())
        order.updated_at = min(shipped_at, now)
    elif order.status == OrderStatus.DELIVERED:
        delivered_at = created + timedelta(days=rng.randint(3, 6))
        order.estimated_delivery = delivered_at.date()
        order.updated_at = delivered_at
    else:  # cancelled within a day
        order.updated_at = created + timedelta(hours=rng.randint(1, 20))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="delete all existing data first")
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.reset:
            reset(db)
        elif db.scalar(select(func.count()).select_from(User)):
            sys.exit("The database already contains data. Use --reset to wipe it and seed again.")
        counts = seed(db)

    print("Seeded:", ", ".join(f"{n} {k}" for k, n in counts.items()))
    print(f"\nDemo accounts (password for all: {DEMO_PASSWORD})")
    for email, role in STAFF:
        print(f"  {role.value:<8} {email}")
    for _name, email in CUSTOMERS:
        print(f"  CUSTOMER {email}")


if __name__ == "__main__":
    main()
