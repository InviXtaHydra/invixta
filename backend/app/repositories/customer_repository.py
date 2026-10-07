from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer


class CustomerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, customer_id: int) -> Customer | None:
        return self.db.get(Customer, customer_id)

    def exists(self, customer_id: int) -> bool:
        return self.db.scalar(select(Customer.id).where(Customer.id == customer_id)) is not None
