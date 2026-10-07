from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import OrderStatus, User
from app.schemas.common import Page
from app.schemas.order import OrderRead, OrderSummary
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=Page[OrderSummary])
def list_orders(
    status: OrderStatus | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[OrderSummary]:
    """Your orders, newest first. Staff (ADMIN/AGENT) see all orders."""
    orders, total = OrderService(db).list_orders(user, status=status, limit=limit, offset=offset)
    return Page(items=[OrderSummary.from_order(o) for o in orders], total=total, limit=limit, offset=offset)


@router.get("/{order_id}", response_model=OrderRead, responses={404: {"description": "Order not found (or not yours)"}})
def get_order(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> OrderRead:
    return OrderRead.from_order(OrderService(db).get_order(user, order_id))
