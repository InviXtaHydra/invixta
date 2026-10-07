from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas.auth import PasswordChangeRequest, UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.from_user(user)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT, responses={400: {"description": "Current password is wrong"}})
def change_password(body: PasswordChangeRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    """Change your own password. Existing tokens stay valid until they expire."""
    AuthService(db).change_password(user, current_password=body.current_password, new_password=body.new_password)
