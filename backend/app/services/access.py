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
