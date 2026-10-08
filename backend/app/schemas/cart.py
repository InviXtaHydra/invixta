from decimal import Decimal

from pydantic import BaseModel, Field

from app.models import Cart, ProductCategory
from app.schemas.catalog import TeamRead
from app.services.cart_service import cart_totals, line_price


class CartItemAdd(BaseModel):
    variant_id: int
    quantity: int = Field(1, ge=1, le=10)
    personalization_name: str | None = Field(None, max_length=12, description="Printed on the back, e.g. 'DE VRIES'")
    personalization_number: int | None = Field(None, ge=0, le=99)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=10)


class CartLine(BaseModel):
    id: int
    variant_id: int
    product_slug: str
    product_name: str
    category: ProductCategory
    season: str | None
    team: TeamRead | None
    size: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    personalization_name: str | None
    personalization_number: int | None
    stock: int


class CartRead(BaseModel):
    token: str | None = Field(description="Guest carts only: send it back as the X-Cart-Token header")
    items: list[CartLine]
    item_count: int
    subtotal: Decimal
    shipping_estimate: Decimal = Field(description="Standard shipping to the Netherlands")
    free_shipping_remaining: Decimal

    @classmethod
    def from_cart(cls, cart: Cart | None) -> "CartRead":
        totals = cart_totals(cart)
        lines = []
        for item in cart.items if cart else []:
            product = item.variant.product
            price = line_price(item)
            lines.append(
                CartLine(
                    id=item.id,
                    variant_id=item.variant_id,
                    product_slug=product.slug,
                    product_name=product.name,
                    category=product.category,
                    season=product.season,
                    team=TeamRead.model_validate(product.team) if product.team else None,
                    size=item.variant.size,
                    quantity=item.quantity,
                    unit_price=price,
                    line_total=price * item.quantity,
                    personalization_name=item.personalization_name,
                    personalization_number=item.personalization_number,
                    stock=item.variant.stock,
                )
            )
        return cls(
            token=cart.token if cart else None,
            items=lines,
            item_count=totals.item_count,
            subtotal=totals.subtotal,
            shipping_estimate=totals.shipping_estimate,
            free_shipping_remaining=totals.free_shipping_remaining,
        )


class CartQuote(BaseModel):
    subtotal: Decimal
    shipping_cost: Decimal
    total: Decimal
