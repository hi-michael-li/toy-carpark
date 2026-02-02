from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from src.core.dependencies import DB, ActiveUser
from src.core.exceptions import AuthenticationError
from src.core.security import decode_token
from src.schemas.auth import RegisterRequest, Token, TokenRefresh
from src.schemas.common import MessageResponse
from src.schemas.user import UserResponse
from src.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=dict)
async def register(db: DB, data: RegisterRequest):
    user, token = await auth_service.register_user(db, data)
    return {"user": user, "access_token": token.access_token, "refresh_token": token.refresh_token}


@router.post("/login", response_model=Token)
async def login(db: DB, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    from src.schemas.auth import LoginRequest

    data = LoginRequest(email=form_data.username, password=form_data.password)
    return await auth_service.authenticate_user(db, data)


@router.post("/refresh", response_model=Token)
async def refresh_token(db: DB, data: TokenRefresh):
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise AuthenticationError("Invalid refresh token")

    user_id = int(payload.get("sub", 0))
    return await auth_service.refresh_access_token(db, user_id)


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: ActiveUser):
    return MessageResponse(message="Successfully logged out")


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: ActiveUser):
    return UserResponse.model_validate(current_user)
