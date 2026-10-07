"""Test setup: a real PostgreSQL test database, migrated with Alembic, and one rolled-back
transaction per test so tests never see each other's data."""

import os
from collections.abc import Iterator
from decimal import Decimal

# Point the app at the test database *before* any app module creates its engine.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError("Set TEST_DATABASE_URL (see .env.example) to run the tests")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from alembic import command  # noqa: E402
from app.core.database import get_db  # noqa: E402
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Customer, Order, OrderItem, OrderStatus, Product, SupportTicket, User, UserRole  # noqa: E402

PASSWORD = "CorrectHorse9"


def _create_test_database() -> None:
    url = make_url(TEST_DATABASE_URL)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": url.database})
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def engine() -> Iterator[object]:
    _create_test_database()
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    cfg.attributes["url"] = TEST_DATABASE_URL
    command.downgrade(cfg, "base")  # start from an empty schema every run
    command.upgrade(cfg, "head")
    eng = create_engine(TEST_DATABASE_URL)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine) -> Iterator[Session]:  # type: ignore[no-untyped-def]
    """A session inside a transaction that is rolled back after the test.

    Service code calls commit(); with join_transaction_mode="create_savepoint" those commits only
    release savepoints, so the outer transaction can still undo everything.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# --- Test data helpers ------------------------------------------------------------------------


def make_customer(db: Session, email: str, name: str = "Test Customer") -> User:
    user = User(email=email, password_hash=hash_password(PASSWORD), role=UserRole.CUSTOMER)
    user.customer = Customer(name=name, email=email)
    db.add(user)
    db.flush()
    return user


def make_staff(db: Session, email: str, role: UserRole) -> User:
    user = User(email=email, password_hash=hash_password(PASSWORD), role=role)
    db.add(user)
    db.flush()
    return user


def make_order(db: Session, customer: Customer, status: OrderStatus = OrderStatus.SHIPPED, quantity: int = 2) -> Order:
    product = Product(name="Test Mug", description="Ceramic", price=Decimal("12.50"), stock=10)
    db.add(product)
    db.flush()
    order = Order(
        customer_id=customer.id,
        status=status,
        total_amount=Decimal("12.50") * quantity,
        carrier="PostNL",
        tracking_number="PO123456789",
    )
    order.items.append(OrderItem(product_id=product.id, quantity=quantity, price=product.price))
    db.add(order)
    db.flush()
    return order


def make_ticket(db: Session, customer: Customer, subject: str = "Broken item") -> SupportTicket:
    ticket = SupportTicket(customer_id=customer.id, subject=subject, description="The item arrived broken in the box.")
    db.add(ticket)
    db.flush()
    return ticket


def auth_header(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


@pytest.fixture
def alice(db: Session) -> User:
    return make_customer(db, "alice@example.com", "Alice")


@pytest.fixture
def bob(db: Session) -> User:
    return make_customer(db, "bob@example.com", "Bob")
