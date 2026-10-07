from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.auth import RegisterRequest, TokenResponse, UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> UserRead:
    """Create a customer account. New accounts always get the CUSTOMER role."""
    user = AuthService(db).register(email=body.email, password=body.password, name=body.name)
    return UserRead.from_user(user)


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenResponse:
    """OAuth2 password flow: send `username` (your email) and `password` as form fields."""
    return TokenResponse(access_token=AuthService(db).login(email=form.username, password=form.password))
