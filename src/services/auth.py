from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AuthenticationError, ConflictError
from src.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from src.models.user import User
from src.schemas.auth import LoginRequest, RegisterRequest, Token
from src.schemas.user import UserResponse
from src.utils.constants import UserRole


async def register_user(db: AsyncSession, data: RegisterRequest) -> tuple[UserResponse, Token]:
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise ConflictError("Email already registered")

    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=UserRole.CUSTOMER,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    token = Token(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token(user.id),
    )

    return UserResponse.model_validate(user), token


async def authenticate_user(db: AsyncSession, data: LoginRequest) -> Token:
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise AuthenticationError("Invalid email or password")

    if not user.is_active:
        raise AuthenticationError("User account is disabled")

    return Token(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token(user.id),
    )


async def refresh_access_token(db: AsyncSession, user_id: int) -> Token:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError("User not found")

    return Token(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token(user.id),
    )
