"""The catalogue: fictional clubs, their products, and one variant per size with its own stock."""

from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ProductCategory
from app.models.mixins import CreatedAtMixin, pg_enum


class Team(Base):
    """A fictional football club. The colours and pattern are used to draw its shirts in the shop."""

    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("slug", name="uq_teams_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(120))
    short_name: Mapped[str] = mapped_column(String(12))  # e.g. "DIJ", printed on the crest
    league: Mapped[str] = mapped_column(String(80), index=True)
    city: Mapped[str] = mapped_column(String(80))
    founded: Mapped[int]
    primary_color: Mapped[str] = mapped_column(String(7))  # "#C8102E"
    secondary_color: Mapped[str] = mapped_column(String(7))
    pattern: Mapped[str] = mapped_column(String(20))  # plain | stripes | hoops | halves | sash

    products: Mapped[list["Product"]] = relationship(back_populates="team")


class Product(CreatedAtMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_products_price_non_negative"),
        CheckConstraint("compare_at_price IS NULL OR compare_at_price > price", name="ck_products_compare_at_above_price"),
        UniqueConstraint("slug", name="uq_products_slug"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[ProductCategory] = mapped_column(pg_enum(ProductCategory, "product_category"), index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL", name="fk_products_team_id_teams"), index=True)
    season: Mapped[str | None] = mapped_column(String(10))  # "26/27", or the original year for retro shirts
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # money: exact decimal, never float
    compare_at_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))  # the old price when on sale
    personalizable: Mapped[bool] = mapped_column(Boolean, default=False)  # name + number printing possible
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    team: Mapped["Team | None"] = relationship(back_populates="products")
    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductVariant.position"
    )


class ProductVariant(Base):
    """One size of a product. Stock is kept per size: an M can be sold out while an L is not."""

    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("product_id", "size", name="uq_product_variants_product_size"),
        UniqueConstraint("sku", name="uq_product_variants_sku"),
        CheckConstraint("stock >= 0", name="ck_product_variants_stock_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    size: Mapped[str] = mapped_column(String(12))  # "M", "140", "One size"
    sku: Mapped[str] = mapped_column(String(40))
    stock: Mapped[int] = mapped_column(default=0)
    position: Mapped[int] = mapped_column(default=0)  # display order: S, M, L, XL, …

    product: Mapped["Product"] = relationship(back_populates="variants")
