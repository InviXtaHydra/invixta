from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Order, OrderItem, OrderStatus, Product


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, *, customer_id: int | None, status: OrderStatus | None = None, limit: int = 20, offset: int = 0) -> list[Order]:
        query = select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc(), Order.id.desc())
        if customer_id is not None:
            query = query.where(Order.customer_id == customer_id)
        if status is not None:
            query = query.where(Order.status == status)
        return list(self.db.scalars(query.limit(limit).offset(offset)))

    def count(self, *, customer_id: int | None, status: OrderStatus | None = None) -> int:
        query = select(func.count()).select_from(Order)
        if customer_id is not None:
            query = query.where(Order.customer_id == customer_id)
        if status is not None:
            query = query.where(Order.status == status)
        return self.db.scalar(query) or 0

    def get(self, order_id: int, *, customer_id: int | None) -> Order | None:
        """Fetch one order with its items and products. With customer_id, only that customer's order."""
        query = (
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.product).selectinload(Product.team))
            .where(Order.id == order_id)
        )
        if customer_id is not None:
            query = query.where(Order.customer_id == customer_id)
        return self.db.scalar(query)
