"""Password hashing (bcrypt) and JWT access tokens (PyJWT)."""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import get_settings
from app.models.enums import UserRole

# bcrypt only uses the first 72 bytes of a password; the API rejects longer passwords.
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


# Used to spend the same time on unknown emails, so login timing doesn't reveal which emails exist.
DUMMY_PASSWORD_HASH = hash_password("not-a-real-password")


def create_access_token(user_id: int, role: UserRole) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int | None:
    """Returns the user id, or None when the token is invalid, expired or tampered with."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm], options={"require": ["exp", "sub"]})
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        return None
