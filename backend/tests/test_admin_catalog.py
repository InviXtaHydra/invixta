"""Admin product management: prices, sales, visibility and stock."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, UserRole
from tests.conftest import auth_header, make_product, make_staff


def test_admin_changes_price_sale_visibility_and_stock(client: TestClient, db: Session) -> None:
    admin = make_staff(db, "admin@example.com", UserRole.ADMIN)
    headers = auth_header(admin)
    product = make_product(db, "FC Test Home", "69.95", {"M": 5, "L": 0})

    listed = client.get("/admin/products", params={"q": "FC Test"}, headers=headers).json()
    assert listed["total"] == 1 and [v["size"] for v in listed["items"][0]["variants"]] == ["M", "L"]

    sale = client.patch(f"/admin/products/{product.id}", json={"price": "49.95", "compare_at_price": "69.95"}, headers=headers)
    assert sale.status_code == 200 and sale.json()["compare_at_price"] == "69.95"
    assert client.get(f"/catalog/products/{product.slug}").json()["discount_percent"] == 29

    ended = client.patch(f"/admin/products/{product.id}", json={"compare_at_price": None}, headers=headers).json()
    assert ended["compare_at_price"] is None and ended["price"] == "49.95"
    assert client.patch(f"/admin/products/{product.id}", json={"compare_at_price": "40.00"}, headers=headers).status_code == 400

    large = product.variants[1]
    assert client.patch(f"/admin/variants/{large.id}", json={"stock": 12}, headers=headers).json()["stock"] == 12
    assert client.patch(f"/admin/variants/{large.id}", json={"stock": -1}, headers=headers).status_code == 422

    hidden = client.patch(f"/admin/products/{product.id}", json={"is_active": False}, headers=headers).json()
    assert hidden["is_active"] is False
    assert client.get(f"/catalog/products/{product.slug}").status_code == 404  # gone from the shop
    assert client.get("/admin/products", params={"q": "FC Test"}, headers=headers).json()["total"] == 1  # still in the admin


def test_product_admin_is_admin_only(client: TestClient, db: Session, alice: User) -> None:
    agent = make_staff(db, "agent@example.com", UserRole.AGENT)
    product = make_product(db, "FC Test Home")
    for user in (alice, agent):
        assert client.get("/admin/products", headers=auth_header(user)).status_code == 403
        assert client.patch(f"/admin/products/{product.id}", json={"is_active": False}, headers=auth_header(user)).status_code == 403
        assert client.patch(f"/admin/variants/{product.variants[0].id}", json={"stock": 0}, headers=auth_header(user)).status_code == 403
