"""Pricing rules and the public catalogue."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.models import ProductCategory, ShippingMethod
from app.services.pricing import shipping_cost
from tests.conftest import make_product, make_team


@pytest.mark.parametrize(
    ("country", "method", "subtotal", "expected"),
    [
        ("NL", ShippingMethod.STANDARD, "49.99", "4.95"),
        ("NL", ShippingMethod.STANDARD, "50.00", "0"),  # free from €50
        ("BE", ShippingMethod.EXPRESS, "84.95", "7.50"),  # express surcharge also above €50
        ("BE", ShippingMethod.EXPRESS, "20.00", "12.45"),
        ("DE", ShippingMethod.STANDARD, "20.00", "9.95"),  # EU rate outside the Benelux
        ("LU", ShippingMethod.STANDARD, "20.00", "4.95"),
    ],
)
def test_shipping_cost(country: str, method: ShippingMethod, subtotal: str, expected: str) -> None:
    assert shipping_cost(country, method, Decimal(subtotal)) == Decimal(expected)


def test_express_only_in_nl_and_be_and_only_eu_countries() -> None:
    with pytest.raises(BadRequestError, match="Express"):
        shipping_cost("DE", ShippingMethod.EXPRESS, Decimal("10"))
    with pytest.raises(BadRequestError, match="don't ship"):
        shipping_cost("US", ShippingMethod.STANDARD, Decimal("10"))


def test_catalogue_filters_and_sorting(client: TestClient, db: Session) -> None:
    dijkstad = make_team(db, "fc-dijkstad", "FC Dijkstad")
    polder = make_team(db, "polder-united", "Polder United")
    home = make_product(
        db, "FC Dijkstad Home", "69.95", {"M": 0, "L": 4}, category=ProductCategory.HOME, team=dijkstad, personalizable=True
    )
    make_product(db, "Polder United Home", "49.95", {"M": 3}, category=ProductCategory.HOME, team=polder, compare_at_price="69.95")
    make_product(db, "Invixta Ball", "29.95", {"One size": 5})

    def names(**params: str | int | bool) -> list[str]:
        response = client.get("/catalog/products", params=params)
        assert response.status_code == 200
        return [p["name"] for p in response.json()["items"]]

    assert names(category="home", sort="price_asc") == ["Polder United Home", "FC Dijkstad Home"]
    assert names(team="fc-dijkstad") == ["FC Dijkstad Home"]
    assert names(size="M", category="home") == ["Polder United Home"]  # Dijkstad is sold out in M
    assert names(on_sale=True) == ["Polder United Home"]
    assert names(q="dijkstad home") == ["FC Dijkstad Home"]
    assert names(max_price=30) == ["Invixta Ball"]

    detail = client.get(f"/catalog/products/{home.slug}").json()
    assert [(v["size"], v["stock"]) for v in detail["variants"]] == [("M", 0), ("L", 4)]
    assert detail["sizes_in_stock"] == ["L"] and detail["team"]["primary_color"] == "#C8102E"
    assert detail["personalization_price"] == "15.00"
    sale = client.get("/catalog/products", params={"on_sale": True}).json()["items"][0]
    assert sale["discount_percent"] == 29


def test_inactive_products_are_hidden(client: TestClient, db: Session) -> None:
    product = make_product(db, "Old Shirt")
    product.is_active = False
    db.flush()
    assert client.get(f"/catalog/products/{product.slug}").status_code == 404
    assert client.get("/catalog/products", params={"q": "Old Shirt"}).json()["total"] == 0


def test_leagues_group_the_clubs(client: TestClient, db: Session) -> None:
    make_team(db, "fc-a", "FC A")
    make_team(db, "fc-b", "FC B")
    [league] = client.get("/catalog/leagues").json()
    assert league["name"] == "Test League" and [t["name"] for t in league["teams"]] == ["FC A", "FC B"]
