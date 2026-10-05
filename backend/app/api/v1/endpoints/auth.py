
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseSession
from app.models import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services.security import create_access_token, verify_password


router = APIRouter(prefix="/auth", tags=["authentication"])


# Existing login endpoint — accepts JSON for the frontend
@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: DatabaseSession,
) -> TokenResponse:
    user = db.scalar(
        select(User).where(User.email == payload.email.lower())
    )

    if (
        user is None
        or not verify_password(payload.password, user.password_hash)
        or not user.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        user=UserResponse.model_validate(user),
    )


# New OAuth2 endpoint — supports Swagger Authorize
@router.post("/token", response_model=TokenResponse)
def swagger_token(
    db: DatabaseSession,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> TokenResponse:
    user = db.scalar(
        select(User).where(
            User.email == form_data.username.lower()
        )
    )

    if (
        user is None
        or not verify_password(form_data.password, user.password_hash)
        or not user.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        user=UserResponse.model_validate(user),
    )


# Existing endpoint — returns the logged-in user
@router.get("/me", response_model=UserResponse)
def current_user(
    current_user: CurrentUser,
) -> UserResponse:
    return UserResponse.model_validate(current_user)
