from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models import Product, ProductCategory, Team
from app.services.pricing import discount_percent


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    short_name: str
    league: str
    city: str
    founded: int
    primary_color: str
    secondary_color: str
    pattern: str


class VariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    size: str
    sku: str
    stock: int


class ProductSummary(BaseModel):
    id: int
    slug: str
    name: str
    category: ProductCategory
    season: str | None
    price: Decimal
    compare_at_price: Decimal | None
    discount_percent: int | None
    personalizable: bool
    team: TeamRead | None
    sizes_in_stock: list[str]

    @classmethod
    def from_product(cls, product: Product) -> "ProductSummary":
        return cls.model_validate(_summary(product))


class ProductRead(ProductSummary):
    description: str
    variants: list[VariantRead]
    personalization_price: Decimal

    @classmethod
    def from_product_with_price(cls, product: Product, personalization_price: Decimal) -> "ProductRead":
        return cls.model_validate(
            {
                **_summary(product),
                "description": product.description,
                "variants": [VariantRead.model_validate(v) for v in product.variants],
                "personalization_price": personalization_price,
            }
        )


class League(BaseModel):
    name: str
    teams: list[TeamRead]

    @classmethod
    def group(cls, teams: list[Team]) -> list["League"]:
        leagues: dict[str, list[TeamRead]] = {}
        for team in teams:
            leagues.setdefault(team.league, []).append(TeamRead.model_validate(team))
        return [cls(name=name, teams=members) for name, members in leagues.items()]


def _summary(product: Product) -> dict[str, object]:
    return {
        "id": product.id,
        "slug": product.slug,
        "name": product.name,
        "category": product.category,
        "season": product.season,
        "price": product.price,
        "compare_at_price": product.compare_at_price,
        "discount_percent": discount_percent(product),
        "personalizable": product.personalizable,
        "team": TeamRead.model_validate(product.team) if product.team else None,
        "sizes_in_stock": [v.size for v in product.variants if v.stock > 0],
    }
