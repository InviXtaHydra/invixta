from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.models import User
from app.schemas.auth import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.from_user(user)
