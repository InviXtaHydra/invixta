from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models import ProductCategory


class AdminVariant(BaseModel):
    id: int
    size: str
    sku: str
    stock: int


class AdminProduct(BaseModel):
    id: int
    slug: str
    name: str
    category: ProductCategory
    team: str | None
    price: Decimal
    compare_at_price: Decimal | None
    is_active: bool
    personalizable: bool
    units_sold: int
    variants: list[AdminVariant]


class ProductUpdate(BaseModel):
    """Only the fields that are sent change. Send compare_at_price: null to end a sale."""

    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    compare_at_price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    is_active: bool | None = None

    @model_validator(mode="after")
    def sale_price_below_old_price(self) -> "ProductUpdate":
        if self.price is not None and self.compare_at_price is not None and self.compare_at_price <= self.price:
            raise ValueError("The old price (compare_at_price) must be higher than the price")
        return self


class StockUpdate(BaseModel):
    stock: int = Field(ge=0, le=10000)
