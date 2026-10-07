from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Identity, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import OrderStatus
from app.models.mixins import TimestampMixin, pg_enum

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.product import Product


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    # Order numbers start at 10001 so they look like real order numbers ("#10482").
    id: Mapped[int] = mapped_column(Identity(start=10001), primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True)
    status: Mapped[OrderStatus] = mapped_column(pg_enum(OrderStatus, "order_status"), default=OrderStatus.PENDING)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    tracking_number: Mapped[str | None] = mapped_column(String(64))
    carrier: Mapped[str | None] = mapped_column(String(64))
    estimated_delivery: Mapped[date | None] = mapped_column(Date)

    customer: Mapped["Customer"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    quantity: Mapped[int]
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # unit price at the time of purchase

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()
