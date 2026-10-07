from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import Order, OrderStatus, User
from app.repositories.order_repository import OrderRepository
from app.services.access import customer_scope, scope_for


class OrderService:
    def __init__(self, db: Session) -> None:
        self.orders = OrderRepository(db)

    def list_orders(
        self, user: User, *, customer_id: int | None = None, status: OrderStatus | None, limit: int, offset: int
    ) -> tuple[list[Order], int]:
        scope = scope_for(user, customer_id)
        return (
            self.orders.list(customer_id=scope, status=status, limit=limit, offset=offset),
            self.orders.count(customer_id=scope, status=status),
        )

    def get_order(self, user: User, order_id: int) -> Order:
        # Someone else's order gives the same 404 as a non-existent one: we don't reveal that it exists.
        order = self.orders.get(order_id, customer_id=customer_scope(user))
        if order is None:
            raise NotFoundError(f"Order {order_id} not found")
        return order
