from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models import Order, OrderItem
from app.models.enums import OrderStatus, PaymentMethod, PaymentStatus, ShippingMethod


class OrderItemRead(BaseModel):
    product_id: int
    product_name: str
    size: str | None
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    personalization_name: str | None
    personalization_number: int | None

    @classmethod
    def from_item(cls, item: OrderItem) -> "OrderItemRead":
        return cls(
            product_id=item.product_id,
            product_name=item.product_name or item.product.name,
            size=item.size,
            quantity=item.quantity,
            unit_price=item.price,
            line_total=item.price * item.quantity,
            personalization_name=item.personalization_name,
            personalization_number=item.personalization_number,
        )


class OrderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    status: OrderStatus
    subtotal: Decimal
    shipping_cost: Decimal
    total_amount: Decimal
    payment_status: PaymentStatus
    payment_method: PaymentMethod | None
    shipping_method: ShippingMethod
    tracking_number: str | None
    carrier: str | None
    estimated_delivery: date | None
    created_at: datetime
    updated_at: datetime
    item_count: int

    @classmethod
    def from_order(cls, order: Order) -> "OrderSummary":
        return cls.model_validate({**_base(order), "item_count": sum(i.quantity for i in order.items)})


class OrderRead(OrderSummary):
    items: list[OrderItemRead]
    shipping_name: str | None
    shipping_street: str | None
    shipping_postcode: str | None
    shipping_city: str | None
    shipping_country: str | None
    paid_at: datetime | None
    shipped_at: datetime | None
    delivered_at: datetime | None
    cancelled_at: datetime | None
    can_cancel: bool

    @classmethod
    def from_order(cls, order: Order) -> "OrderRead":
        return cls.model_validate(
            {
                **_base(order),
                "item_count": sum(i.quantity for i in order.items),
                "items": [OrderItemRead.from_item(i) for i in order.items],
                "shipping_name": order.shipping_name,
                "shipping_street": order.shipping_street,
                "shipping_postcode": order.shipping_postcode,
                "shipping_city": order.shipping_city,
                "shipping_country": order.shipping_country,
                "paid_at": order.paid_at,
                "shipped_at": order.shipped_at,
                "delivered_at": order.delivered_at,
                "cancelled_at": order.cancelled_at,
                "can_cancel": order.status in (OrderStatus.PENDING, OrderStatus.PROCESSING),
            }
        )


def _base(order: Order) -> dict[str, object]:
    return {
        "id": order.id,
        "customer_id": order.customer_id,
        "status": order.status,
        "subtotal": order.subtotal,
        "shipping_cost": order.shipping_cost,
        "total_amount": order.total_amount,
        "payment_status": order.payment_status,
        "payment_method": order.payment_method,
        "shipping_method": order.shipping_method,
        "tracking_number": order.tracking_number,
        "carrier": order.carrier,
        "estimated_delivery": order.estimated_delivery,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }
