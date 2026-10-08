"""The shopping cart: guests and signed-in users, stock limits, printing."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import ProductCategory, User
from tests.conftest import auth_header, make_product


def shirt(db: Session, stock: int = 5, personalizable: bool = True):  # type: ignore[no-untyped-def]
    return make_product(db, "FC Test Home", "69.95", {"M": stock, "L": 0}, category=ProductCategory.HOME, personalizable=personalizable)


def test_guest_cart_with_a_printed_shirt(client: TestClient, db: Session) -> None:
    variant = shirt(db).variants[0]
    body = client.post(
        "/cart/items", json={"variant_id": variant.id, "quantity": 2, "personalization_name": " de  vries ", "personalization_number": 10}
    ).json()
    assert body["token"]  # a new guest cart
    [line] = body["items"]
    assert line["personalization_name"] == "DE VRIES" and line["personalization_number"] == 10
    assert line["unit_price"] == "84.95" and line["line_total"] == "169.90"  # €69.95 + €15 printing
    assert body["subtotal"] == "169.90" and body["shipping_estimate"] == "0" and body["free_shipping_remaining"] == "0"

    headers = {"X-Cart-Token": body["token"]}
    assert client.get("/cart", headers=headers).json()["item_count"] == 2
    assert client.get("/cart").json()["items"] == []  # without the token: no cart


def test_same_item_twice_is_one_line_and_different_names_are_two(client: TestClient, db: Session, alice: User) -> None:
    variant = shirt(db).variants[0]
    headers = auth_header(alice)
    client.post("/cart/items", json={"variant_id": variant.id}, headers=headers)
    client.post("/cart/items", json={"variant_id": variant.id}, headers=headers)
    body = client.post("/cart/items", json={"variant_id": variant.id, "personalization_number": 7}, headers=headers).json()
    assert [(i["quantity"], i["personalization_number"]) for i in body["items"]] == [(2, None), (1, 7)]
    assert body["token"] is None  # an account cart has no token


def test_stock_limits(client: TestClient, db: Session, alice: User) -> None:
    product = shirt(db, stock=3)
    medium, large = product.variants
    headers = auth_header(alice)
    assert client.post("/cart/items", json={"variant_id": large.id}, headers=headers).status_code == 409  # sold out
    assert client.post("/cart/items", json={"variant_id": medium.id, "quantity": 2}, headers=headers).status_code == 200
    # Another 2 with a name: 4 in total, but only 3 in stock.
    response = client.post("/cart/items", json={"variant_id": medium.id, "quantity": 2, "personalization_name": "INVIXTA"}, headers=headers)
    assert response.status_code == 409 and "Only 1 left" in response.json()["detail"]

    line_id = client.get("/cart", headers=headers).json()["items"][0]["id"]
    assert client.patch(f"/cart/items/{line_id}", json={"quantity": 3}, headers=headers).status_code == 200
    assert client.patch(f"/cart/items/{line_id}", json={"quantity": 4}, headers=headers).status_code == 409
    assert client.patch(f"/cart/items/{line_id}", json={"quantity": 11}, headers=headers).status_code == 422
    assert client.delete(f"/cart/items/{line_id}", headers=headers).json()["items"] == []


def test_printing_rules(client: TestClient, db: Session, alice: User) -> None:
    headers = auth_header(alice)
    ball = make_product(db, "Ball").variants[0]
    variant = shirt(db).variants[0]
    assert client.post("/cart/items", json={"variant_id": ball.id, "personalization_name": "BOB"}, headers=headers).status_code == 400
    assert (
        client.post("/cart/items", json={"variant_id": variant.id, "personalization_name": "<script>"}, headers=headers).status_code == 400
    )
    assert client.post("/cart/items", json={"variant_id": variant.id, "personalization_number": 100}, headers=headers).status_code == 422
    assert client.post("/cart/items", json={"variant_id": 999999}, headers=headers).status_code == 404


def test_guest_cart_is_merged_into_the_account_after_login(client: TestClient, db: Session, alice: User) -> None:
    variant = shirt(db, stock=4).variants[0]
    headers = auth_header(alice)
    client.post("/cart/items", json={"variant_id": variant.id, "quantity": 3}, headers=headers)
    token = client.post("/cart/items", json={"variant_id": variant.id, "quantity": 2}).json()["token"]

    merged = client.post("/cart/claim", headers={**headers, "X-Cart-Token": token}).json()
    assert [i["quantity"] for i in merged["items"]] == [4]  # 3 + 2, capped at the 4 in stock
    assert client.get("/cart", headers={"X-Cart-Token": token}).json()["items"] == []  # the guest cart is gone


def test_carts_are_private(client: TestClient, db: Session, alice: User, bob: User) -> None:
    variant = shirt(db).variants[0]
    line_id = client.post("/cart/items", json={"variant_id": variant.id}, headers=auth_header(alice)).json()["items"][0]["id"]
    assert client.delete(f"/cart/items/{line_id}", headers=auth_header(bob)).status_code == 404
    assert client.get("/cart", headers=auth_header(bob)).json()["items"] == []
    assert client.get("/cart", headers={"Authorization": "Bearer not-a-token"}).status_code == 401


def test_quote_uses_the_checkout_rules(client: TestClient, db: Session, alice: User) -> None:
    headers = auth_header(alice)
    client.post("/cart/items", json={"variant_id": make_product(db, "Socks", "12.95").variants[0].id}, headers=headers)
    assert client.get("/cart/quote", params={"country": "nl"}, headers=headers).json() == {
        "subtotal": "12.95",
        "shipping_cost": "4.95",
        "total": "17.90",
    }
    assert client.get("/cart/quote", params={"country": "DE"}, headers=headers).json()["shipping_cost"] == "9.95"
    assert client.get("/cart/quote", params={"country": "DE", "shipping_method": "express"}, headers=headers).status_code == 400
