from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AuthenticationError, AuthorizationError
from src.core.security import decode_token
from src.database import async_session_maker
from src.models.user import User
from src.utils.constants import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    payload = decode_token(token)
    if payload is None:
        raise AuthenticationError()

    token_type = payload.get("type")
    if token_type != "access":
        raise AuthenticationError("Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError()

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError("User not found")

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise AuthorizationError("Inactive user")
    return current_user


async def get_current_admin(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise AuthorizationError("Admin access required")
    return current_user


async def get_current_operator(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    if current_user.role not in [UserRole.OPERATOR, UserRole.ADMIN]:
        raise AuthorizationError("Operator access required")
    return current_user


class PaginationParams:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ):
        self.page = page
        self.limit = limit
        self.offset = (page - 1) * limit


# Type aliases for cleaner dependency injection
DB = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
ActiveUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(get_current_admin)]
OperatorUser = Annotated[User, Depends(get_current_operator)]
Pagination = Annotated[PaginationParams, Depends()]
