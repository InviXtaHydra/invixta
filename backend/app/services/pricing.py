"""Prices and shipping costs. Pure functions: the server always calculates prices itself and never
trusts a price sent by the browser."""

from decimal import Decimal

from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.models import Product, ShippingMethod

# Countries we ship to (EU only), with their names for the checkout form.
SHIPPING_COUNTRIES: dict[str, str] = {
    "NL": "Netherlands",
    "BE": "Belgium",
    "LU": "Luxembourg",
    "DE": "Germany",
    "FR": "France",
    "AT": "Austria",
    "DK": "Denmark",
    "ES": "Spain",
    "IE": "Ireland",
    "IT": "Italy",
    "PT": "Portugal",
}
BENELUX = {"NL", "BE", "LU"}
EXPRESS_COUNTRIES = {"NL", "BE"}


def unit_price(product: Product, personalized: bool) -> Decimal:
    """Price of one item, including name/number printing."""
    return product.price + (get_settings().personalization_price if personalized else Decimal("0"))


def shipping_cost(country: str, method: ShippingMethod, subtotal: Decimal) -> Decimal:
    """Standard: free from FREE_SHIPPING_FROM, otherwise a Benelux or EU rate. Express adds a surcharge."""
    settings = get_settings()
    if country not in SHIPPING_COUNTRIES:
        raise BadRequestError(f"We don't ship to {country}. We deliver within the EU.")
    if method == ShippingMethod.EXPRESS and country not in EXPRESS_COUNTRIES:
        raise BadRequestError("Express delivery is only available in the Netherlands and Belgium")
    if subtotal >= settings.free_shipping_from:
        base = Decimal("0")
    else:
        base = settings.shipping_benelux if country in BENELUX else settings.shipping_eu
    return base + (settings.express_surcharge if method == ShippingMethod.EXPRESS else Decimal("0"))


def discount_percent(product: Product) -> int | None:
    if not product.compare_at_price:
        return None
    return round((1 - product.price / product.compare_at_price) * 100)
