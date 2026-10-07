from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import DUMMY_PASSWORD_HASH, create_access_token, hash_password, verify_password
from app.models import User
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def register(self, *, email: str, password: str, name: str) -> User:
        email = email.lower()
        if self.users.get_by_email(email):
            raise ConflictError("An account with this email already exists")
        try:
            user = self.users.create_with_customer(email=email, password_hash=hash_password(password), name=name)
            self.db.commit()
        except IntegrityError as exc:  # two registrations racing for the same email
            self.db.rollback()
            raise ConflictError("An account with this email already exists") from exc
        return user

    def login(self, *, email: str, password: str) -> str:
        user = self.users.get_by_email(email.lower())
        # Always run bcrypt, even for unknown emails, so response time doesn't leak which emails exist.
        valid = verify_password(password, user.password_hash if user else DUMMY_PASSWORD_HASH)
        if not user or not valid:
            raise AuthenticationError("Incorrect email or password")
        return create_access_token(user.id, user.role)
