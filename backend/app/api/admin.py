from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import User, UserRole
from app.schemas.admin_catalog import AdminProduct, AdminVariant, ProductUpdate, StockUpdate
from app.schemas.common import Page
from app.schemas.metrics import MetricsRead
from app.services.admin_catalog_service import AdminCatalogService
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/metrics", response_model=MetricsRead)
def metrics(
    days: int = Query(14, ge=1, le=90, description="Length of the daily activity series"),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> MetricsRead:
    """Usage of the AI assistant: conversations, latency, tool calls, RAG searches, tickets and the
    questions it couldn't answer (useful to see which documents are missing)."""
    return MetricsRead.model_validate(MetricsService(db).collect(days))


admin_only = require_roles(UserRole.ADMIN)


@router.get("/products", response_model=Page[AdminProduct])
def list_products(
    q: str | None = Query(None, max_length=100),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> Page[AdminProduct]:
    """All products, also hidden ones, with stock per size and units sold."""
    items, total = AdminCatalogService(db).list_products(q, limit, offset)
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.patch("/products/{product_id}", response_model=AdminProduct)
def update_product(product_id: int, body: ProductUpdate, _: User = Depends(admin_only), db: Session = Depends(get_db)) -> AdminProduct:
    """Change the price, start or end a sale (compare_at_price), or hide/show a product in the shop."""
    return AdminCatalogService(db).update(product_id, body)


@router.patch("/variants/{variant_id}", response_model=AdminVariant)
def update_stock(variant_id: int, body: StockUpdate, _: User = Depends(admin_only), db: Session = Depends(get_db)) -> AdminVariant:
    """Set the stock of one size."""
    return AdminCatalogService(db).set_stock(variant_id, body.stock)
