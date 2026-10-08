"""Admin: product prices, sales, visibility and stock per size."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BadRequestError, NotFoundError
from app.models import Order, OrderItem, OrderStatus, Product, ProductVariant, Team
from app.schemas.admin_catalog import AdminProduct, AdminVariant, ProductUpdate


class AdminCatalogService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_products(self, q: str | None, limit: int, offset: int) -> tuple[list[AdminProduct], int]:
        query = select(Product).outerjoin(Team, Product.team_id == Team.id)
        if q:
            for word in q.split()[:5]:
                query = query.where(Product.name.ilike(f"%{word}%") | Team.name.ilike(f"%{word}%"))
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        products = list(
            self.db.scalars(
                query.options(selectinload(Product.variants), selectinload(Product.team)).order_by(Product.name).limit(limit).offset(offset)
            )
        )
        sold = self._units_sold([p.id for p in products])
        return [self._read(p, sold.get(p.id, 0)) for p in products], total

    def update(self, product_id: int, body: ProductUpdate) -> AdminProduct:
        product = self._product(product_id)
        fields = body.model_fields_set
        price = body.price if "price" in fields and body.price is not None else product.price
        compare_at = body.compare_at_price if "compare_at_price" in fields else product.compare_at_price
        if compare_at is not None and compare_at <= price:
            raise BadRequestError("The old price must be higher than the price (or empty to end the sale)")
        product.price = price
        product.compare_at_price = compare_at
        if body.is_active is not None:
            product.is_active = body.is_active
        self.db.commit()
        return self._read(product, self._units_sold([product.id]).get(product.id, 0))

    def set_stock(self, variant_id: int, stock: int) -> AdminVariant:
        variant = self.db.get(ProductVariant, variant_id, with_for_update=True)
        if variant is None:
            raise NotFoundError(f"Size {variant_id} not found")
        variant.stock = stock
        self.db.commit()
        return AdminVariant(id=variant.id, size=variant.size, sku=variant.sku, stock=variant.stock)

    def _product(self, product_id: int) -> Product:
        product = self.db.scalar(
            select(Product).options(selectinload(Product.variants), selectinload(Product.team)).where(Product.id == product_id)
        )
        if product is None:
            raise NotFoundError(f"Product {product_id} not found")
        return product

    def _units_sold(self, product_ids: list[int]) -> dict[int, int]:
        rows = self.db.execute(
            select(OrderItem.product_id, func.sum(OrderItem.quantity))
            .join(Order, Order.id == OrderItem.order_id)
            .where(OrderItem.product_id.in_(product_ids), Order.status != OrderStatus.CANCELLED)
            .group_by(OrderItem.product_id)
        ).all()
        return {pid: int(n) for pid, n in rows}

    @staticmethod
    def _read(product: Product, units_sold: int) -> AdminProduct:
        return AdminProduct(
            id=product.id,
            slug=product.slug,
            name=product.name,
            category=product.category,
            team=product.team.name if product.team else None,
            price=product.price,
            compare_at_price=product.compare_at_price,
            is_active=product.is_active,
            personalizable=product.personalizable,
            units_sold=units_sold,
            variants=[AdminVariant(id=v.id, size=v.size, sku=v.sku, stock=v.stock) for v in product.variants],
        )
