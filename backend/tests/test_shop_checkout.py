"""Checkout, simulated payments, cancelling and the fulfillment simulator."""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Order, OrderStatus, ProductCategory, ProductVariant, User, UserRole
from app.services.fulfillment_service import FulfillmentService
from tests.conftest import auth_header, make_product, make_staff

ADDRESS = {"name": "Alice Test", "street": "Lindelaan 12", "postcode": "3511 AB", "city": "Utrecht", "country": "nl"}


def fill_cart(client: TestClient, db: Session, user: User, stock: int = 5, quantity: int = 1, price: str = "69.95") -> ProductVariant:
    product = make_product(db, "FC Test Home", price, {"M": stock}, category=ProductCategory.HOME, personalizable=True)
    variant = product.variants[0]
    body = {"variant_id": variant.id, "quantity": quantity, "personalization_name": "ALICE", "personalization_number": 9}
    assert client.post("/cart/items", json=body, headers=auth_header(user)).status_code == 200
    return variant


def checkout(client: TestClient, user: User, **overrides: Any) -> Any:
    return client.post("/checkout", json={**ADDRESS, "payment_method": "ideal", **overrides}, headers=auth_header(user))


def test_checkout_creates_an_order_with_server_side_prices_and_reserves_stock(client: TestClient, db: Session, alice: User) -> None:
    variant = fill_cart(client, db, alice, stock=5, quantity=2)
    response = checkout(client, alice, shipping_method="express")
    assert response.status_code == 201, response.text
    order, payment = response.json()["order"], response.json()["payment"]

    assert order["status"] == "pending" and order["payment_status"] == "pending"
    assert order["subtotal"] == "169.90"  # 2 x (69.95 + 15.00 printing)
    assert order["shipping_cost"] == "7.50"  # free standard shipping, plus the express surcharge
    assert order["total_amount"] == "177.40" and payment["amount"] == "177.40"
    assert order["shipping_country"] == "NL" and order["can_cancel"] is True
    [item] = order["items"]
    assert (item["size"], item["personalization_name"], item["personalization_number"]) == ("M", "ALICE", 9)

    db.refresh(variant)
    assert variant.stock == 3  # reserved
    assert client.get("/cart", headers=auth_header(alice)).json()["items"] == []  # cart emptied


def test_checkout_validation(client: TestClient, db: Session, alice: User) -> None:
    assert checkout(client, alice).status_code == 400  # empty cart
    fill_cart(client, db, alice)
    assert checkout(client, alice, country="US").status_code == 422
    assert checkout(client, alice, country="DE", shipping_method="express").status_code == 400
    assert checkout(client, alice, payment_method="bitcoin").status_code == 422
    assert checkout(client, alice, street="").status_code == 422


def test_checkout_fails_when_stock_ran_out_in_the_meantime(client: TestClient, db: Session, alice: User) -> None:
    variant = fill_cart(client, db, alice, stock=2, quantity=2)
    variant.stock = 1  # someone else bought one
    db.flush()
    response = checkout(client, alice)
    assert response.status_code == 409 and "only 1 left" in response.json()["detail"]
    db.refresh(variant)
    assert variant.stock == 1


def test_staff_cannot_check_out(client: TestClient, db: Session) -> None:
    agent = make_staff(db, "agent@example.com", UserRole.AGENT)
    assert checkout(client, agent).status_code == 403


def test_approved_payment_moves_the_order_to_processing(client: TestClient, db: Session, alice: User) -> None:
    fill_cart(client, db, alice)
    body = checkout(client, alice).json()
    headers = auth_header(alice)
    paid = client.post(f"/payments/{body['payment']['id']}/complete", json={"outcome": "approve"}, headers=headers)
    assert paid.json()["status"] == "paid"
    order = client.get(f"/orders/{body['order']['id']}", headers=headers).json()
    assert order["status"] == "processing" and order["payment_status"] == "paid" and order["paid_at"]
    # Paying twice isn't possible.
    assert client.post(f"/payments/{body['payment']['id']}/complete", json={"outcome": "approve"}, headers=headers).status_code == 409


def test_declined_payment_can_be_retried(client: TestClient, db: Session, alice: User) -> None:
    fill_cart(client, db, alice)
    body = checkout(client, alice).json()
    headers = auth_header(alice)
    declined = client.post(f"/payments/{body['payment']['id']}/complete", json={"outcome": "decline"}, headers=headers).json()
    assert declined["status"] == "failed"
    order_id = body["order"]["id"]
    assert client.get(f"/orders/{order_id}", headers=headers).json()["status"] == "pending"

    retry = client.post(f"/orders/{order_id}/payments", json={"payment_method": "bancontact"}, headers=headers)
    assert retry.status_code == 201 and retry.json()["method"] == "bancontact"
    client.post(f"/payments/{retry.json()['id']}/complete", json={"outcome": "approve"}, headers=headers)
    assert client.get(f"/orders/{order_id}", headers=headers).json()["status"] == "processing"
    assert client.post(f"/orders/{order_id}/payments", json={}, headers=headers).status_code == 409  # already paid


def test_payments_and_orders_of_others_are_not_visible(client: TestClient, db: Session, alice: User, bob: User) -> None:
    fill_cart(client, db, alice)
    body = checkout(client, alice).json()
    bob_headers = auth_header(bob)
    assert client.get(f"/payments/{body['payment']['id']}", headers=bob_headers).status_code == 404
    assert client.post(f"/payments/{body['payment']['id']}/complete", json={"outcome": "approve"}, headers=bob_headers).status_code == 404
    assert client.post(f"/orders/{body['order']['id']}/cancel", headers=bob_headers).status_code == 404


def test_cancel_gives_stock_back_and_refunds(client: TestClient, db: Session, alice: User) -> None:
    variant = fill_cart(client, db, alice, stock=5, quantity=2)
    body = checkout(client, alice).json()
    headers = auth_header(alice)
    client.post(f"/payments/{body['payment']['id']}/complete", json={"outcome": "approve"}, headers=headers)

    cancelled = client.post(f"/orders/{body['order']['id']}/cancel", headers=headers).json()
    assert cancelled["status"] == "cancelled" and cancelled["payment_status"] == "refunded" and cancelled["can_cancel"] is False
    db.refresh(variant)
    assert variant.stock == 5
    assert client.post(f"/orders/{body['order']['id']}/cancel", headers=headers).status_code == 409


def test_shipped_orders_cannot_be_cancelled(client: TestClient, db: Session, alice: User) -> None:
    fill_cart(client, db, alice)
    body = checkout(client, alice).json()
    order = db.get(Order, body["order"]["id"])
    assert order is not None
    order.status = OrderStatus.SHIPPED
    db.flush()
    response = client.post(f"/orders/{order.id}/cancel", headers=auth_header(alice))
    assert response.status_code == 409 and "haven't shipped" in response.json()["detail"]


def test_fulfillment_simulator_ships_delivers_and_cancels(client: TestClient, db: Session, alice: User) -> None:
    headers = auth_header(alice)
    fill_cart(client, db, alice)
    paid = checkout(client, alice).json()
    client.post(f"/payments/{paid['payment']['id']}/complete", json={"outcome": "approve"}, headers=headers)
    variant = fill_cart(client, db, alice, stock=4, quantity=1)
    unpaid = checkout(client, alice).json()
    db.expire_all()

    now = datetime.now(UTC)
    simulator = FulfillmentService(db)
    assert simulator.advance(now).shipped == 0  # too early

    result = simulator.advance(now + timedelta(minutes=4))
    assert result.shipped == 1
    shipped = db.get(Order, paid["order"]["id"])
    assert shipped is not None and shipped.status == OrderStatus.SHIPPED
    assert shipped.carrier == "PostNL" and shipped.tracking_number and shipped.tracking_number.startswith("3S")

    result = simulator.advance(now + timedelta(minutes=15))
    assert result.delivered == 1

    result = simulator.advance(now + timedelta(minutes=31))
    assert result.cancelled == 1
    cancelled = db.scalar(select(Order).where(Order.id == unpaid["order"]["id"]))
    assert cancelled is not None and cancelled.status == OrderStatus.CANCELLED
    db.refresh(variant)
    assert variant.stock == 4  # the reserved shirt is back in stock
