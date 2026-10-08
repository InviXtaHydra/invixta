"""Payments. There is no real payment provider: the shop's "TestPay" page lets you approve or decline
a payment, which is how a real provider (iDEAL, Bancontact, …) reports back. No money moves."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import PaymentMethod, PaymentStatus
from app.models.mixins import CreatedAtMixin, pg_enum

if TYPE_CHECKING:
    from app.models.order import Order


class Payment(CreatedAtMixin, Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    method: Mapped[PaymentMethod] = mapped_column(pg_enum(PaymentMethod, "payment_method"))
    status: Mapped[PaymentStatus] = mapped_column(pg_enum(PaymentStatus, "payment_status"), default=PaymentStatus.PENDING)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    order: Mapped["Order"] = relationship(back_populates="payments")
