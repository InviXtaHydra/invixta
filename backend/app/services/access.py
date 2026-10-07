"""Shared authorization rule: customers only see their own data, staff (ADMIN/AGENT) see everything."""

from app.models import User, UserRole

STAFF_ROLES = {UserRole.ADMIN, UserRole.AGENT}


def is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


def customer_scope(user: User) -> int | None:
    """The customer id a query must be limited to, or None for staff (no limit).

    A customer account without a profile gets -1, which matches nothing — never "everything".
    """
    if is_staff(user):
        return None
    return user.customer.id if user.customer else -1


def scope_for(user: User, requested_customer_id: int | None) -> int | None:
    """Like customer_scope, but staff may narrow the query to one customer."""
    scope = customer_scope(user)
    return requested_customer_id if scope is None and requested_customer_id is not None else scope
