"""The demo data script runs and produces a consistent shop."""

import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Order, OrderStatus, PaymentStatus, Product, ProductVariant

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if not SCRIPTS.exists():  # inside the container the scripts live in /app/scripts
    SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))


def test_seed_creates_a_consistent_shop(db: Session) -> None:
    import seed_database

    counts = seed_database.seed(db)
    assert counts["teams"] == 12 and counts["products"] == 70 and counts["orders"] == 20
    assert db.scalar(select(func.count()).select_from(ProductVariant).where(ProductVariant.stock < 0)) == 0
    assert db.scalar(select(func.count()).select_from(Product).where(~Product.variants.any())) == 0

    for order in db.scalars(select(Order)):
        assert order.total_amount == order.subtotal + order.shipping_cost
        assert order.subtotal == sum((i.price * i.quantity for i in order.items), Decimal("0"))
        if order.status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            assert order.carrier and order.tracking_number and order.payment_status == PaymentStatus.PAID
        if order.status == OrderStatus.PROCESSING:
            assert order.payment_status == PaymentStatus.PAID and order.paid_at
