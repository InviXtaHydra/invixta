"""The public catalogue: no account needed to browse."""

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models import ProductCategory
from app.repositories.catalog_repository import CatalogRepository, ProductFilters, Sort
from app.schemas.catalog import League, ProductRead, ProductSummary
from app.schemas.common import Page

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/products", response_model=Page[ProductSummary])
def list_products(
    category: ProductCategory | None = None,
    team: str | None = Query(None, max_length=80, description="Team slug"),
    league: str | None = Query(None, max_length=80),
    size: str | None = Query(None, max_length=12, description="Only products with this size in stock"),
    q: str | None = Query(None, max_length=100, description="Search in product and team names"),
    min_price: Decimal | None = Query(None, ge=0),
    max_price: Decimal | None = Query(None, ge=0),
    on_sale: bool = False,
    sort: Sort = "popular",
    limit: int = Query(24, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> Page[ProductSummary]:
    """Products with filters. `popular` sorts by units actually sold."""
    filters = ProductFilters(category, team, league, size, q, min_price, max_price, on_sale)
    repo = CatalogRepository(db)
    products = repo.list(filters, sort, limit, offset)
    return Page(items=[ProductSummary.from_product(p) for p in products], total=repo.count(filters), limit=limit, offset=offset)


@router.get("/products/{slug}", response_model=ProductRead, responses={404: {"description": "Product not found"}})
def get_product(slug: str, db: Session = Depends(get_db)) -> ProductRead:
    product = CatalogRepository(db).get_by_slug(slug)
    if product is None:
        raise NotFoundError(f"Product '{slug}' not found")
    return ProductRead.from_product_with_price(product, get_settings().personalization_price)


@router.get("/leagues", response_model=list[League])
def leagues(db: Session = Depends(get_db)) -> list[League]:
    """Leagues with their clubs, for the shop's menu."""
    return League.group(CatalogRepository(db).teams())
