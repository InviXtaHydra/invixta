"""Fill the database with the fictional Kopbal shop: clubs, products, stock, customers, orders, tickets.

Run inside the backend container:
    docker compose exec backend python scripts/seed_database.py          # only if the database is empty
    docker compose exec backend python scripts/seed_database.py --reset  # wipe and re-seed

After --reset, index the knowledge base again: python scripts/ingest_documents.py
All demo accounts use the password printed at the end. Never run --reset against real data.
"""

import argparse
import random
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import cast

# Make `import app` work when the script is run from /app/scripts.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from catalog_data import ACCESSORIES, ADULT_SIZES, LEAGUES, RETRO, RETRO_SHIRTS, SCARF_PRICE, TEAMS, team_products
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
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
    Payment,
    PaymentMethod,
    PaymentStatus,
    Product,
    ProductCategory,
    ProductVariant,
    ShippingMethod,
    SupportTicket,
    Team,
    TicketPriority,
    TicketStatus,
    User,
    UserRole,
)
from app.services.checkout_service import estimated_delivery
from app.services.fulfillment_service import TRACKING_PREFIX, carrier_for
from app.services.pricing import shipping_cost

DEMO_PASSWORD = "Password123!"

STAFF = [
    ("admin@kopbal.shop", UserRole.ADMIN),
    ("agent@kopbal.shop", UserRole.AGENT),
]

# (name, email, street, postcode, city, country)
CUSTOMERS = [
    ("Emma de Vries", "emma.devries@example.com", "Lindelaan 12", "3511 AB", "Utrecht", "NL"),
    ("Lucas Janssens", "lucas.janssens@example.com", "Kerkstraat 48", "2000", "Antwerpen", "BE"),
    ("Sofia Martens", "sofia.martens@example.com", "Rozengracht 7", "1016 LT", "Amsterdam", "NL"),
    ("Noah Peeters", "noah.peeters@example.com", "Stationsplein 3", "9000", "Gent", "BE"),
    ("Mila Claes", "mila.claes@example.com", "Am Hafen 21", "50667", "Köln", "DE"),
]

SHIRT_NAMES = ["DE VRIES", "JANSSENS", "MARTENS", "PEETERS", "CLAES", "KOPBAL", "VAN DIJK", "MERTENS"]

# How many days ago the 20 orders were placed. Their status follows from their age (see _status_for_age),
# like in a real shop: recent orders are still open, older ones are delivered (or cancelled).
ORDER_AGES_DAYS = [0, 1, 2, 3, 4, 5, 6, 8, 9, 11, 13, 16, 21, 27, 34, 41, 48, 57, 66, 83]

TICKETS = [
    # (customer index, subject, description, status, priority)
    (
        0,
        "Shirt arrived with a misprinted name",
        "The name on the back of my FC Dijkstad shirt says DE VRIE instead of DE VRIES.",
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
        "Size exchange",
        "The Polder United away shirt in M is too small. Can I swap it for an L?",
        TicketStatus.IN_PROGRESS,
        TicketPriority.MEDIUM,
    ),
    (
        1,
        "Invoice with VAT number",
        "I need an invoice with my company VAT number for the shirts I ordered for our team.",
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
    (
        3,
        "Wrong club in my parcel",
        "I ordered a Haven Rovers home shirt but received a Kanaal City shirt.",
        TicketStatus.OPEN,
        TicketPriority.HIGH,
    ),
    (
        4,
        "Question about the retro shirts",
        "Is the 1988 FC Dijkstad retro shirt the same fit as the new home shirt?",
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
    (
        2,
        [
            (MessageRole.USER, "Can I return a shirt with my name printed on it?"),
            (MessageRole.ASSISTANT, "I'll look that up in our policy documents."),
        ],
    ),
]


def reset(db: Session) -> None:
    tables = (
        "messages, conversations, support_tickets, payments, order_items, orders, cart_items, carts, "
        "product_variants, products, teams, customers, users, document_chunks, documents"
    )
    db.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    # RESTART IDENTITY resets order numbers to the column's START value (10001).
    db.commit()


def seed_catalog(db: Session, rng: random.Random, now: datetime) -> list[Product]:
    teams: dict[str, Team] = {}
    for slug, name, short, league, city, founded, primary, secondary, pattern in TEAMS:
        teams[slug] = Team(
            slug=slug, name=name, short_name=short, league=LEAGUES[league], city=city, founded=founded,
            primary_color=primary, secondary_color=secondary, pattern=pattern,
        )  # fmt: skip
    db.add_all(teams.values())
    db.flush()

    specs: list[dict[str, object]] = []
    for i, (slug, name, _short, _league, city, founded, *_rest) in enumerate(TEAMS):
        for spec in team_products(slug, name, city, founded, sale=i % 4 == 1):
            specs.append({**spec, "team": teams[slug]})
        specs.append(
            {
                "slug": f"{slug}-scarf", "name": f"{name} Scarf", "category": ProductCategory.ACCESSORY, "season": None,
                "price": SCARF_PRICE, "compare_at_price": None, "personalizable": False, "sizes": ["One size"], "team": teams[slug],
                "description": f"Knitted {name} scarf in the club colours, 140 x 18 cm.",
            }
        )  # fmt: skip
    for slug, year, story in RETRO_SHIRTS:
        team = teams[slug]
        specs.append(
            {
                "slug": f"{slug}-retro-{year}", "name": f"{team.name} Retro Shirt {year}", "category": ProductCategory.RETRO,
                "season": year, "price": RETRO, "compare_at_price": None, "personalizable": True, "sizes": ADULT_SIZES, "team": team,
                "description": f"A faithful remake of the {year} shirt from {story}. Heavier cotton-blend fabric with a classic, "
                "slightly wider fit.",
            }
        )  # fmt: skip
    for slug, name, price, compare_at, sizes, description in ACCESSORIES:
        specs.append(
            {
                "slug": slug, "name": name, "category": ProductCategory.ACCESSORY, "season": None, "price": price,
                "compare_at_price": compare_at, "personalizable": False, "sizes": sizes, "team": None, "description": description,
            }
        )  # fmt: skip

    products = []
    for n, spec in enumerate(specs):
        sizes = cast(list[str], spec.pop("sizes"))
        product = Product(**spec, created_at=now - timedelta(days=120 - n))
        for position, size in enumerate(sizes):
            # Mostly in stock, a few sizes low or sold out, like a real shop.
            stock = rng.choice([0, 2, 8, 15, 25, 30, 40, 60])
            product.variants.append(
                ProductVariant(size=size, sku=f"KB-{n + 1:03d}-{size.replace(' ', '')}", stock=stock, position=position)
            )
        products.append(product)
    db.add_all(products)
    db.flush()
    return products


def seed(db: Session) -> dict[str, int]:
    rng = random.Random(42)  # deterministic: the same data on every run
    now = datetime.now(UTC)
    password_hash = hash_password(DEMO_PASSWORD)  # hashed once; bcrypt is deliberately slow
    personalization_price = get_settings().personalization_price

    for email, role in STAFF:
        db.add(User(email=email, password_hash=password_hash, role=role))

    customers: list[tuple[Customer, tuple[str, str, str, str]]] = []
    for i, (name, email, street, postcode, city, country) in enumerate(CUSTOMERS):
        user = User(email=email, password_hash=password_hash, role=UserRole.CUSTOMER, created_at=now - timedelta(days=200 - i * 20))
        user.customer = Customer(name=name, email=email, created_at=user.created_at)
        db.add(user)
        customers.append((user.customer, (street, postcode, city, country)))

    products = seed_catalog(db, rng, now)

    # Oldest first, so order numbers (10001, 10002, …) increase with the order date.
    orders: list[Order] = []
    for age in sorted(ORDER_AGES_DAYS, reverse=True):
        customer, (street, postcode, city, country) = rng.choice(customers)
        created_at = now - timedelta(days=age, hours=rng.randint(0, 20))
        method = ShippingMethod.EXPRESS if country in ("NL", "BE") and rng.random() < 0.2 else ShippingMethod.STANDARD
        order = Order(
            customer_id=customer.id, status=_status_for_age(age, rng), created_at=created_at, total_amount=Decimal("0"),
            shipping_name=customer.name, shipping_street=street, shipping_postcode=postcode, shipping_city=city,
            shipping_country=country, shipping_method=method, payment_method=rng.choice(list(PaymentMethod)),
        )  # fmt: skip
        for product in rng.sample(products, k=rng.randint(1, 3)):
            variant = rng.choice(product.variants)
            printed = product.personalizable and rng.random() < 0.4
            order.items.append(
                OrderItem(
                    product_id=product.id, variant_id=variant.id, quantity=rng.randint(1, 2), product_name=product.name,
                    size=variant.size, price=product.price + (personalization_price if printed else Decimal("0")),
                    personalization_name=rng.choice(SHIRT_NAMES) if printed else None,
                    personalization_number=rng.randint(1, 23) if printed else None,
                )
            )  # fmt: skip
        order.subtotal = sum((i.price * i.quantity for i in order.items), Decimal("0"))
        order.shipping_cost = shipping_cost(country, method, order.subtotal)
        order.total_amount = order.subtotal + order.shipping_cost
        _set_timeline(order, age, rng, now)
        orders.append(order)
    db.add_all(orders)

    for idx, subject, description, status, priority in TICKETS:
        created = now - timedelta(days=rng.randint(1, 30))
        db.add(
            SupportTicket(
                customer_id=customers[idx][0].id, subject=subject, description=description, status=status,
                priority=priority, created_at=created, updated_at=created,
            )
        )  # fmt: skip

    for idx, messages in CONVERSATIONS:
        conv = Conversation(customer_id=customers[idx][0].id)
        for message_role, content in messages:
            conv.messages.append(Message(role=message_role, content=content))
        db.add(conv)

    db.commit()
    return {
        "users": db.scalar(select(func.count()).select_from(User)) or 0,
        "customers": len(customers),
        "teams": len(TEAMS),
        "products": len(products),
        "variants": db.scalar(select(func.count()).select_from(ProductVariant)) or 0,
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


def _set_timeline(order: Order, age_days: int, rng: random.Random, now: datetime) -> None:
    """Payment, shipping and delivery dates, carrier and tracking number, consistent with the status."""
    created = order.created_at
    paid = order.status != OrderStatus.PENDING and not (order.status == OrderStatus.CANCELLED and rng.random() < 0.5)
    payment = Payment(amount=order.total_amount, method=order.payment_method or PaymentMethod.IDEAL, created_at=created)
    if paid:
        order.paid_at = payment.decided_at = created + timedelta(minutes=rng.randint(1, 10))
        payment.status = order.payment_status = PaymentStatus.PAID
    else:
        payment.status = PaymentStatus.PENDING if order.status == OrderStatus.PENDING else PaymentStatus.FAILED
        order.payment_status = PaymentStatus.PENDING if order.status == OrderStatus.PENDING else PaymentStatus.FAILED
    order.payments.append(payment)

    if order.status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
        order.carrier = carrier_for(order.shipping_country, rng)
        order.tracking_number = f"{TRACKING_PREFIX[order.carrier]}{rng.randint(10**9, 10**10 - 1)}"
        order.shipped_at = created + timedelta(days=min(2, age_days - 1 if age_days > 1 else 1), hours=rng.randint(1, 8))

    if order.status in (OrderStatus.PENDING, OrderStatus.PROCESSING):
        order.estimated_delivery = estimated_delivery(order, now.date())
        order.updated_at = order.paid_at or created
    elif order.status == OrderStatus.SHIPPED:
        assert order.shipped_at is not None
        # Still in transit: the estimate is today or later.
        order.estimated_delivery = max(now.date(), estimated_delivery(order, order.shipped_at.date()))
        order.updated_at = min(order.shipped_at, now)
    elif order.status == OrderStatus.DELIVERED:
        assert order.shipped_at is not None
        order.delivered_at = order.shipped_at + timedelta(days=rng.randint(1, 3))
        order.estimated_delivery = order.delivered_at.date()
        order.updated_at = order.delivered_at
    else:  # cancelled within a day; a paid cancelled order was refunded
        order.cancelled_at = created + timedelta(hours=rng.randint(1, 20))
        order.updated_at = order.cancelled_at
        if paid:
            payment.status = order.payment_status = PaymentStatus.REFUNDED


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
    print(f"\nDemo accounts (password: {DEMO_PASSWORD})")
    for email, role in STAFF:
        print(f"  {role.value:<8} {email}")
    for _name, email, *_ in CUSTOMERS:
        print(f"  CUSTOMER {email}")


if __name__ == "__main__":
    main()
