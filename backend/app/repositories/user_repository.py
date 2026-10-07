from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Customer, User, UserRole


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.scalar(select(User).options(selectinload(User.customer)).where(User.id == user_id))

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).options(selectinload(User.customer)).where(User.email == email))

    def create_with_customer(self, *, email: str, password_hash: str, name: str) -> User:
        """Create a CUSTOMER user plus its customer profile in one transaction step."""
        user = User(email=email, password_hash=password_hash, role=UserRole.CUSTOMER)
        user.customer = Customer(name=name, email=email)
        self.db.add(user)
        self.db.flush()
        return user
