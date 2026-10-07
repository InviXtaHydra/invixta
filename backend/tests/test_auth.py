from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Customer, User, UserRole
from tests.conftest import PASSWORD, auth_header


def register(client: TestClient, email: str = "new@example.com", password: str = "Sup3rSecret!", name: str = "New Person"):  # type: ignore[no-untyped-def]
    return client.post("/auth/register", json={"email": email, "password": password, "name": name})


def login(client: TestClient, email: str, password: str):  # type: ignore[no-untyped-def]
    return client.post("/auth/login", data={"username": email, "password": password})


class TestRegistration:
    def test_creates_customer_account_with_profile(self, client: TestClient, db: Session) -> None:
        response = register(client, email="New@Example.com")
        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "new@example.com"  # normalised to lower case
        assert body["role"] == "CUSTOMER"
        assert body["customer_id"] is not None
        assert "password" not in body and "password_hash" not in body

        user = db.scalar(select(User).where(User.email == "new@example.com"))
        assert user is not None
        assert user.password_hash != "Sup3rSecret!"  # stored hashed, never plain text
        assert db.scalar(select(Customer).where(Customer.user_id == user.id)) is not None

    def test_duplicate_email_is_rejected_case_insensitively(self, client: TestClient) -> None:
        assert register(client, email="dup@example.com").status_code == 201
        response = register(client, email="DUP@example.com")
        assert response.status_code == 409

    def test_cannot_register_as_admin(self, client: TestClient) -> None:
        response = client.post("/auth/register", json={"email": "x@example.com", "password": "Sup3rSecret!", "name": "X", "role": "ADMIN"})
        assert response.status_code == 201
        assert response.json()["role"] == "CUSTOMER"

    def test_validates_input(self, client: TestClient) -> None:
        assert register(client, email="not-an-email").status_code == 422
        assert register(client, password="short").status_code == 422
        assert register(client, password="x" * 73).status_code == 422  # longer than bcrypt's 72-byte limit
        assert register(client, name="   ").status_code == 422


class TestLogin:
    def test_returns_a_valid_jwt(self, client: TestClient, alice: User) -> None:
        response = login(client, "alice@example.com", PASSWORD)
        assert response.status_code == 200
        body = response.json()
        assert body["token_type"] == "bearer"
        payload = jwt.decode(body["access_token"], get_settings().jwt_secret_key, algorithms=["HS256"])
        assert payload["sub"] == str(alice.id)
        assert payload["role"] == "CUSTOMER"

    def test_email_is_case_insensitive(self, client: TestClient, alice: User) -> None:
        assert login(client, "ALICE@example.com", PASSWORD).status_code == 200

    def test_wrong_password_is_rejected(self, client: TestClient, alice: User) -> None:
        response = login(client, "alice@example.com", "wrong-password")
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password"

    def test_unknown_email_gets_the_same_error(self, client: TestClient) -> None:
        response = login(client, "nobody@example.com", PASSWORD)
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password"


class TestCurrentUser:
    def test_me_returns_the_logged_in_user(self, client: TestClient, alice: User) -> None:
        token = login(client, "alice@example.com", PASSWORD).json()["access_token"]
        response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["email"] == "alice@example.com"
        assert response.json()["name"] == "Alice"

    def test_requires_a_token(self, client: TestClient) -> None:
        response = client.get("/users/me")
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"

    def test_rejects_a_tampered_token(self, client: TestClient, alice: User) -> None:
        token = auth_header(alice)["Authorization"].split()[1]
        header, payload, signature = token.split(".")
        tampered = f"{header}.{payload}.{signature[::-1]}"
        assert client.get("/users/me", headers={"Authorization": f"Bearer {tampered}"}).status_code == 401

    def test_rejects_a_token_signed_with_another_key(self, client: TestClient, alice: User) -> None:
        forged = jwt.encode({"sub": str(alice.id), "exp": datetime.now(UTC) + timedelta(hours=1)}, "x" * 40, algorithm="HS256")
        assert client.get("/users/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401

    def test_rejects_an_expired_token(self, client: TestClient, alice: User) -> None:
        expired = jwt.encode(
            {"sub": str(alice.id), "exp": datetime.now(UTC) - timedelta(minutes=1)}, get_settings().jwt_secret_key, algorithm="HS256"
        )
        assert client.get("/users/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401

    def test_staff_user_has_no_customer_profile(self, client: TestClient, db: Session) -> None:
        from tests.conftest import make_staff

        admin = make_staff(db, "admin@example.com", UserRole.ADMIN)
        body = client.get("/users/me", headers=auth_header(admin)).json()
        assert body["role"] == "ADMIN"
        assert body["customer_id"] is None
