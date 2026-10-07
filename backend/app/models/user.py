from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import UserRole
from app.models.mixins import CreatedAtMixin, pg_enum

if TYPE_CHECKING:
    from app.models.customer import Customer


class User(CreatedAtMixin, Base):
    """A login account. Customers additionally have a Customer profile."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(pg_enum(UserRole, "user_role"), default=UserRole.CUSTOMER)

    customer: Mapped["Customer | None"] = relationship(back_populates="user", uselist=False)
