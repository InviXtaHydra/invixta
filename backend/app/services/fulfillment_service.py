"""The fictional warehouse and carrier. In a real shop these updates come from the warehouse system
and the carrier's tracking; here advance() makes them happen after a few minutes:

    processing (paid)  ──after SIMULATION_SHIP_AFTER_MINUTES──▶    shipped (carrier + tracking number)
    shipped            ──after SIMULATION_DELIVER_AFTER_MINUTES──▶ delivered
    pending (unpaid)   ──after SIMULATION_PAYMENT_TIMEOUT_MINUTES──▶ cancelled, stock back

Run it in a loop with scripts/fulfillment_simulator.py (the `simulator` service in docker compose).
"""

import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Order, OrderStatus, PaymentStatus
from app.services.checkout_service import cancel_order, estimated_delivery

logger = logging.getLogger("supportai.fulfillment")

CARRIER_BY_COUNTRY = {"NL": "PostNL", "BE": "bpost", "LU": "bpost", "DE": "DHL"}
TRACKING_PREFIX = {"PostNL": "3S", "bpost": "BP", "DHL": "JD", "DPD": "DP", "UPS": "1Z"}


@dataclass
class AdvanceResult:
    shipped: int = 0
    delivered: int = 0
    cancelled: int = 0


def carrier_for(country: str | None, rng: random.Random) -> str:
    return CARRIER_BY_COUNTRY.get(country or "", rng.choice(["DPD", "UPS"]))


class FulfillmentService:
    def __init__(self, db: Session, rng: random.Random | None = None) -> None:
        self.db = db
        self.rng = rng or random.Random()

    def advance(self, now: datetime) -> AdvanceResult:
        settings = get_settings()
        result = AdvanceResult()

        ship_before = now - timedelta(minutes=settings.simulation_ship_after_minutes)
        for order in self._orders(Order.status == OrderStatus.PROCESSING, Order.paid_at <= ship_before):
            order.status = OrderStatus.SHIPPED
            order.shipped_at = now
            order.carrier = carrier_for(order.shipping_country, self.rng)
            order.tracking_number = f"{TRACKING_PREFIX[order.carrier]}{self.rng.randint(10**9, 10**10 - 1)}"
            order.estimated_delivery = estimated_delivery(order, now.date())
            result.shipped += 1

        deliver_before = now - timedelta(minutes=settings.simulation_deliver_after_minutes)
        for order in self._orders(Order.status == OrderStatus.SHIPPED, Order.shipped_at <= deliver_before):
            order.status = OrderStatus.DELIVERED
            order.delivered_at = now
            result.delivered += 1

        unpaid_before = now - timedelta(minutes=settings.simulation_payment_timeout_minutes)
        for order in self._orders(
            Order.status == OrderStatus.PENDING, Order.payment_status != PaymentStatus.PAID, Order.created_at <= unpaid_before
        ):
            cancel_order(order, now)
            result.cancelled += 1

        self.db.commit()
        if result.shipped or result.delivered or result.cancelled:
            logger.info("fulfillment step", extra={"shipped": result.shipped, "delivered": result.delivered, "cancelled": result.cancelled})
        return result

    def _orders(self, *conditions: object) -> list[Order]:
        # SKIP LOCKED: an order that a customer is cancelling right now is handled on the next round.
        query = select(Order).where(*conditions).order_by(Order.id).with_for_update(skip_locked=True)  # type: ignore[arg-type]
        return list(self.db.scalars(query))
