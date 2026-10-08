"""Checkout, (simulated) payments and cancelling.

    cart ──checkout──▶ order "pending" + payment "pending"   (stock is reserved right away)
                         │
          TestPay page ──┼── approve ──▶ payment "paid", order "processing"
                         └── decline ──▶ payment "failed", order stays "pending": the customer can pay again
    unpaid for too long ──▶ order "cancelled", stock back            (scripts/fulfillment_simulator.py)
    cancel (pending/processing) ──▶ order "cancelled", stock back, a paid payment is "refunded"

No real money moves anywhere: TestPay plays the role of a payment provider such as iDEAL.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from app.models import Order, OrderItem, OrderStatus, Payment, PaymentMethod, PaymentStatus, ShippingMethod, User
from app.repositories.catalog_repository import CatalogRepository
from app.services.access import customer_scope
from app.services.cart_service import CartService, line_price
from app.services.pricing import SHIPPING_COUNTRIES, shipping_cost


@dataclass
class Address:
    name: str
    street: str
    postcode: str
    city: str
    country: str


def add_working_days(start: date, days: int) -> date:
    current = start
    while days > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Monday to Friday
            days -= 1
    return current


def estimated_delivery(order: Order, from_day: date) -> date:
    express = order.shipping_method == ShippingMethod.EXPRESS
    in_benelux = order.shipping_country in {"NL", "BE", "LU"}
    return add_working_days(from_day, 1 if express else 2 if in_benelux else 4)


class CheckoutService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.catalog = CatalogRepository(db)

    def checkout(self, user: User, address: Address, method: ShippingMethod, payment_method: PaymentMethod) -> tuple[Order, Payment]:
        if user.customer is None:
            raise PermissionDeniedError("Only customer accounts can place orders")
        if address.country not in SHIPPING_COUNTRIES:
            raise BadRequestError(f"We don't ship to {address.country}. We deliver within the EU.")
        carts = CartService(self.db)
        cart = carts.find(user, None)
        if cart is None or not cart.items:
            raise BadRequestError("Your cart is empty")

        # Lock the variants until the order is saved, so two customers can't buy the last shirt at once.
        variants = self.catalog.get_variants([i.variant_id for i in cart.items], for_update=True)
        needed: dict[int, int] = {}
        for item in cart.items:
            needed[item.variant_id] = needed.get(item.variant_id, 0) + item.quantity
        for variant_id, quantity in needed.items():
            variant = variants.get(variant_id)
            if variant is None or not variant.product.is_active:
                raise ConflictError("A product in your cart is no longer available")
            if variant.stock < quantity:
                left = f"only {variant.stock} left" if variant.stock else "sold out"
                raise ConflictError(f"{variant.product.name} in size {variant.size}: {left}. Please update your cart.")

        order = Order(
            customer_id=user.customer.id,
            status=OrderStatus.PENDING,
            shipping_name=address.name,
            shipping_street=address.street,
            shipping_postcode=address.postcode,
            shipping_city=address.city,
            shipping_country=address.country,
            shipping_method=method,
            payment_method=payment_method,
            payment_status=PaymentStatus.PENDING,
            total_amount=Decimal("0"),
        )
        for item in cart.items:
            variant = variants[item.variant_id]
            order.items.append(
                OrderItem(
                    product_id=variant.product_id,
                    variant_id=variant.id,
                    quantity=item.quantity,
                    price=line_price(item),
                    product_name=variant.product.name,
                    size=variant.size,
                    personalization_name=item.personalization_name,
                    personalization_number=item.personalization_number,
                )
            )
            variant.stock -= item.quantity  # reserved now; given back if the order is cancelled
        order.subtotal = sum((i.price * i.quantity for i in order.items), Decimal("0"))
        order.shipping_cost = shipping_cost(address.country, method, order.subtotal)
        order.total_amount = order.subtotal + order.shipping_cost
        order.estimated_delivery = estimated_delivery(order, datetime.now(UTC).date())
        payment = Payment(amount=order.total_amount, method=payment_method, status=PaymentStatus.PENDING)
        order.payments.append(payment)
        self.db.add(order)
        carts.clear(cart)
        self.db.commit()
        return order, payment

    # --- payments ---------------------------------------------------------------------------------

    def get_payment(self, user: User, payment_id: int) -> Payment:
        payment = self.db.get(Payment, payment_id)
        scope = customer_scope(user)
        if payment is None or (scope is not None and payment.order.customer_id != scope):
            raise NotFoundError(f"Payment {payment_id} not found")
        return payment

    def complete_payment(self, user: User, payment_id: int, approve: bool) -> Payment:
        """What the payment provider reports back: approved or declined."""
        payment = self.get_payment(user, payment_id)
        order = payment.order
        if payment.status != PaymentStatus.PENDING:
            raise ConflictError(f"This payment is already {payment.status.value}")
        if order.status != OrderStatus.PENDING:
            raise ConflictError(f"Order #{order.id} is {order.status.value} and can't be paid anymore")
        now = datetime.now(UTC)
        payment.decided_at = now
        if approve:
            payment.status = PaymentStatus.PAID
            order.payment_status = PaymentStatus.PAID
            order.paid_at = now
            order.status = OrderStatus.PROCESSING
            order.estimated_delivery = estimated_delivery(order, now.date())
        else:
            payment.status = PaymentStatus.FAILED
            order.payment_status = PaymentStatus.FAILED
        self.db.commit()
        return payment

    def retry_payment(self, user: User, order_id: int, method: PaymentMethod | None) -> Payment:
        order = self._order(user, order_id)
        if order.status != OrderStatus.PENDING or order.payment_status == PaymentStatus.PAID:
            raise ConflictError(f"Order #{order.id} doesn't need a payment")
        for open_payment in order.payments:
            if open_payment.status == PaymentStatus.PENDING:
                open_payment.status = PaymentStatus.FAILED  # replaced by the new attempt
        payment = Payment(amount=order.total_amount, method=method or order.payment_method or PaymentMethod.IDEAL)
        payment.status = PaymentStatus.PENDING
        order.payments.append(payment)
        order.payment_method = payment.method
        order.payment_status = PaymentStatus.PENDING
        self.db.commit()
        return payment

    # --- cancelling -------------------------------------------------------------------------------

    def cancel(self, user: User, order_id: int) -> Order:
        order = self._order(user, order_id)
        if order.status not in (OrderStatus.PENDING, OrderStatus.PROCESSING):
            raise ConflictError(f"Order #{order.id} is {order.status.value}: only orders that haven't shipped yet can be cancelled")
        cancel_order(order, datetime.now(UTC))
        self.db.commit()
        return order

    def _order(self, user: User, order_id: int) -> Order:
        query = select(Order).where(Order.id == order_id)
        scope = customer_scope(user)
        if scope is not None:
            query = query.where(Order.customer_id == scope)
        order = self.db.scalar(query.with_for_update())
        if order is None:
            raise NotFoundError(f"Order {order_id} not found")
        return order


def cancel_order(order: Order, now: datetime) -> None:
    """Cancel, give the reserved stock back and refund a payment that was made."""
    order.status = OrderStatus.CANCELLED
    order.cancelled_at = now
    order.estimated_delivery = None
    for item in order.items:
        if item.variant is not None:
            item.variant.stock += item.quantity
    for payment in order.payments:
        if payment.status == PaymentStatus.PAID:
            payment.status = PaymentStatus.REFUNDED
        elif payment.status == PaymentStatus.PENDING:
            payment.status = PaymentStatus.FAILED
    if order.payment_status == PaymentStatus.PAID:
        order.payment_status = PaymentStatus.REFUNDED
