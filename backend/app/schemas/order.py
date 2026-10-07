from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models import Order, OrderItem
from app.models.enums import OrderStatus


class OrderItemRead(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal

    @classmethod
    def from_item(cls, item: OrderItem) -> "OrderItemRead":
        return cls(
            product_id=item.product_id,
            product_name=item.product.name,
            quantity=item.quantity,
            unit_price=item.price,
            line_total=item.price * item.quantity,
        )


class OrderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    status: OrderStatus
    total_amount: Decimal
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

    @classmethod
    def from_order(cls, order: Order) -> "OrderRead":
        return cls.model_validate(
            {**_base(order), "item_count": sum(i.quantity for i in order.items), "items": [OrderItemRead.from_item(i) for i in order.items]}
        )


def _base(order: Order) -> dict[str, object]:
    return {
        "id": order.id,
        "customer_id": order.customer_id,
        "status": order.status,
        "total_amount": order.total_amount,
        "tracking_number": order.tracking_number,
        "carrier": order.carrier,
        "estimated_delivery": order.estimated_delivery,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }
