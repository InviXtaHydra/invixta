from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import OrderStatus, User, UserRole
from tests.conftest import auth_header, make_order, make_staff


def test_customer_lists_only_their_own_orders(client: TestClient, db: Session, alice: User, bob: User) -> None:
    mine = make_order(db, alice.customer)  # type: ignore[arg-type]
    make_order(db, bob.customer)  # type: ignore[arg-type]

    response = client.get("/orders", headers=auth_header(alice))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [o["id"] for o in body["items"]] == [mine.id]


def test_order_detail_includes_items_and_shipping(client: TestClient, db: Session, alice: User) -> None:
    order = make_order(db, alice.customer, status=OrderStatus.SHIPPED, quantity=2)  # type: ignore[arg-type]

    response = client.get(f"/orders/{order.id}", headers=auth_header(alice))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "shipped"
    assert body["carrier"] == "PostNL"
    assert body["tracking_number"] == "PO123456789"
    assert Decimal(body["total_amount"]) == Decimal("25.00")
    assert body["items"] == [
        {
            "product_id": order.items[0].product_id,
            "product_name": "Test Mug",
            "size": "One size",
            "quantity": 2,
            "unit_price": "12.50",
            "line_total": "25.00",
            "personalization_name": None,
            "personalization_number": None,
        }
    ]


def test_order_numbers_start_at_10001(db: Session, alice: User) -> None:
    order = make_order(db, alice.customer)  # type: ignore[arg-type]
    assert order.id >= 10001


def test_someone_elses_order_looks_like_it_does_not_exist(client: TestClient, db: Session, alice: User, bob: User) -> None:
    bobs_order = make_order(db, bob.customer)  # type: ignore[arg-type]

    other = client.get(f"/orders/{bobs_order.id}", headers=auth_header(alice))
    missing = client.get("/orders/999999", headers=auth_header(alice))
    assert other.status_code == missing.status_code == 404
    assert "PostNL" not in other.text


def test_staff_can_see_every_order(client: TestClient, db: Session, alice: User, bob: User) -> None:
    make_order(db, alice.customer)  # type: ignore[arg-type]
    bobs_order = make_order(db, bob.customer)  # type: ignore[arg-type]
    for role in (UserRole.AGENT, UserRole.ADMIN):
        staff = make_staff(db, f"{role.value.lower()}@example.com", role)
        assert client.get("/orders", headers=auth_header(staff)).json()["total"] == 2
        assert client.get(f"/orders/{bobs_order.id}", headers=auth_header(staff)).status_code == 200


def test_filter_by_status_and_paginate(client: TestClient, db: Session, alice: User) -> None:
    for status in (OrderStatus.SHIPPED, OrderStatus.SHIPPED, OrderStatus.DELIVERED):
        make_order(db, alice.customer, status=status)  # type: ignore[arg-type]

    shipped = client.get("/orders", params={"status": "shipped"}, headers=auth_header(alice)).json()
    assert shipped["total"] == 2
    assert {o["status"] for o in shipped["items"]} == {"shipped"}

    page = client.get("/orders", params={"limit": 1, "offset": 1}, headers=auth_header(alice)).json()
    assert page["total"] == 3 and len(page["items"]) == 1

    assert client.get("/orders", params={"status": "lost"}, headers=auth_header(alice)).status_code == 422
    assert client.get("/orders", params={"limit": 0}, headers=auth_header(alice)).status_code == 422


def test_orders_require_authentication(client: TestClient) -> None:
    assert client.get("/orders").status_code == 401
    assert client.get("/orders/10001").status_code == 401
