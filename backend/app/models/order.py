from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Identity, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import OrderStatus, PaymentMethod, PaymentStatus, ShippingMethod
from app.models.mixins import TimestampMixin, pg_enum

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.payment import Payment
    from app.models.product import Product, ProductVariant


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    # Order numbers start at 10001 so they look like real order numbers ("#10482").
    id: Mapped[int] = mapped_column(Identity(start=10001), primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True)
    status: Mapped[OrderStatus] = mapped_column(pg_enum(OrderStatus, "order_status"), default=OrderStatus.PENDING)

    # Money: subtotal (items incl. printing) + shipping = total. All computed by the server.
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    # Delivery address and method, copied at checkout.
    shipping_name: Mapped[str | None] = mapped_column(String(120))
    shipping_street: Mapped[str | None] = mapped_column(String(200))
    shipping_postcode: Mapped[str | None] = mapped_column(String(16))
    shipping_city: Mapped[str | None] = mapped_column(String(80))
    shipping_country: Mapped[str | None] = mapped_column(String(2))  # ISO code: NL, BE, DE, …
    shipping_method: Mapped[ShippingMethod] = mapped_column(pg_enum(ShippingMethod, "shipping_method"), default=ShippingMethod.STANDARD)

    payment_method: Mapped[PaymentMethod | None] = mapped_column(pg_enum(PaymentMethod, "payment_method"))
    payment_status: Mapped[PaymentStatus] = mapped_column(pg_enum(PaymentStatus, "payment_status"), default=PaymentStatus.PENDING)

    tracking_number: Mapped[str | None] = mapped_column(String(64))
    carrier: Mapped[str | None] = mapped_column(String(64))
    estimated_delivery: Mapped[date | None] = mapped_column(Date)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    customer: Mapped["Customer"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id")
    payments: Mapped[list["Payment"]] = relationship(back_populates="order", cascade="all, delete-orphan", order_by="Payment.id")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    variant_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="SET NULL", name="fk_order_items_variant_id_product_variants")
    )
    quantity: Mapped[int]
    # Copied at checkout, so later changes to the catalogue don't change old orders.
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # unit price incl. printing
    product_name: Mapped[str] = mapped_column(String(200), default="")
    size: Mapped[str | None] = mapped_column(String(12))
    personalization_name: Mapped[str | None] = mapped_column(String(12))
    personalization_number: Mapped[int | None]

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()
    variant: Mapped["ProductVariant | None"] = relationship()
