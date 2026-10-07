import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


def pg_enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    """Native PostgreSQL enum that stores the enum *values* ("shipped"), not the Python names."""
    return Enum(enum_cls, name=name, values_callable=lambda members: [m.value for m in members])
