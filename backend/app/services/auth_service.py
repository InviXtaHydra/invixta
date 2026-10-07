from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, BadRequestError, ConflictError
from app.core.rate_limit import login_limiter
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
        email = email.lower()
        limiter = login_limiter()
        limiter.check(email)  # too many failed attempts for this email → 429
        user = self.users.get_by_email(email)
        # Always run bcrypt, even for unknown emails, so response time doesn't leak which emails exist.
        valid = verify_password(password, user.password_hash if user else DUMMY_PASSWORD_HASH)
        if not user or not valid:
            limiter.record(email)
            raise AuthenticationError("Incorrect email or password")
        return create_access_token(user.id, user.role)

    def change_password(self, user: User, *, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.password_hash):
            raise BadRequestError("Your current password is incorrect")
        if current_password == new_password:
            raise BadRequestError("The new password must be different from the current one")
        user.password_hash = hash_password(new_password)
        self.db.commit()
