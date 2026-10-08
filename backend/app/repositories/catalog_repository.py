import builtins
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import OrderItem, Product, ProductCategory, ProductVariant, Team

Sort = Literal["popular", "new", "price_asc", "price_desc"]


@dataclass
class ProductFilters:
    category: ProductCategory | None = None
    team: str | None = None  # team slug
    league: str | None = None
    size: str | None = None  # only products with this size in stock
    q: str | None = None  # words in the product or team name
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    on_sale: bool = False


class CatalogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _filtered(self, filters: ProductFilters) -> Select[Product]:
        query = select(Product).outerjoin(Team, Product.team_id == Team.id).where(Product.is_active.is_(True))
        if filters.category:
            query = query.where(Product.category == filters.category)
        if filters.team:
            query = query.where(Team.slug == filters.team)
        if filters.league:
            query = query.where(Team.league == filters.league)
        if filters.size:
            in_stock = exists().where(
                ProductVariant.product_id == Product.id, ProductVariant.size == filters.size, ProductVariant.stock > 0
            )
            query = query.where(in_stock)
        if filters.q:
            for word in filters.q.split()[:5]:
                pattern = f"%{word}%"  # bound parameter: no SQL injection, whatever the user types
                query = query.where(or_(Product.name.ilike(pattern), Team.name.ilike(pattern), Team.city.ilike(pattern)))
        if filters.min_price is not None:
            query = query.where(Product.price >= filters.min_price)
        if filters.max_price is not None:
            query = query.where(Product.price <= filters.max_price)
        if filters.on_sale:
            query = query.where(Product.compare_at_price.is_not(None))
        return query

    def list(self, filters: ProductFilters, sort: Sort, limit: int, offset: int) -> builtins.list[Product]:
        query = self._filtered(filters).options(selectinload(Product.variants), selectinload(Product.team))
        if sort == "popular":
            sold = select(func.coalesce(func.sum(OrderItem.quantity), 0)).where(OrderItem.product_id == Product.id).scalar_subquery()
            query = query.order_by(sold.desc(), Product.id)
        elif sort == "new":
            query = query.order_by(Product.created_at.desc(), Product.id.desc())
        elif sort == "price_asc":
            query = query.order_by(Product.price, Product.id)
        else:
            query = query.order_by(Product.price.desc(), Product.id)
        return builtins.list(self.db.scalars(query.limit(limit).offset(offset)))

    def count(self, filters: ProductFilters) -> int:
        return self.db.scalar(select(func.count()).select_from(self._filtered(filters).subquery())) or 0

    def get_by_slug(self, slug: str) -> Product | None:
        query = (
            select(Product)
            .options(selectinload(Product.variants), selectinload(Product.team))
            .where(Product.slug == slug, Product.is_active.is_(True))
        )
        return self.db.scalar(query)

    def teams(self) -> builtins.list[Team]:
        return builtins.list(self.db.scalars(select(Team).order_by(Team.league, Team.name)))

    def get_variants(self, variant_ids: builtins.list[int], *, for_update: bool = False) -> dict[int, ProductVariant]:
        """Variants with their product. for_update locks the rows (checkout), in id order to avoid deadlocks."""
        query = (
            select(ProductVariant)
            .options(selectinload(ProductVariant.product).selectinload(Product.team))
            .where(ProductVariant.id.in_(variant_ids))
            .order_by(ProductVariant.id)
        )
        if for_update:
            query = query.with_for_update(of=ProductVariant)
        return {v.id: v for v in self.db.scalars(query)}
