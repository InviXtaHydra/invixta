"""Unit tests for the authorization rule shared by all services."""

from app.models import Customer, User, UserRole
from app.services.access import customer_scope, is_staff


def test_staff_has_no_customer_scope() -> None:
    for role in (UserRole.ADMIN, UserRole.AGENT):
        user = User(email="s@example.com", password_hash="x", role=role)
        assert is_staff(user)
        assert customer_scope(user) is None


def test_customer_is_scoped_to_their_profile() -> None:
    user = User(email="c@example.com", password_hash="x", role=UserRole.CUSTOMER)
    user.customer = Customer(id=7, name="C", email="c@example.com")
    assert not is_staff(user)
    assert customer_scope(user) == 7


def test_customer_without_profile_matches_nothing() -> None:
    user = User(email="c@example.com", password_hash="x", role=UserRole.CUSTOMER)
    assert customer_scope(user) == -1  # never None, which would mean "everything"
