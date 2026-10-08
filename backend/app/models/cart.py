"""Shopping carts. A signed-in customer has one cart; a guest's cart is found by a random token that
the browser keeps (sent as the X-Cart-Token header) and is merged into the account after login."""

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.product import ProductVariant


class Cart(TimestampMixin, Base):
    __tablename__ = "carts"
    __table_args__ = (UniqueConstraint("token", name="uq_carts_token"), UniqueConstraint("user_id", name="uq_carts_user_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token: Mapped[str | None] = mapped_column(String(64))  # guest carts only

    items: Mapped[list["CartItem"]] = relationship(back_populates="cart", cascade="all, delete-orphan", order_by="CartItem.id")


class CartItem(TimestampMixin, Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        CheckConstraint("quantity BETWEEN 1 AND 10", name="ck_cart_items_quantity_range"),
        CheckConstraint("personalization_number IS NULL OR personalization_number BETWEEN 0 AND 99", name="ck_cart_items_number_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"))
    quantity: Mapped[int]
    # Name/number printing. A printed shirt is its own line: two shirts with different names are two lines.
    personalization_name: Mapped[str | None] = mapped_column(String(12))
    personalization_number: Mapped[int | None]

    cart: Mapped["Cart"] = relationship(back_populates="items")
    variant: Mapped["ProductVariant"] = relationship()
