from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.models.user import User
from src.schemas.user import UserListResponse, UserResponse, UserUpdate
from src.utils.constants import UserRole


async def get_user_by_id(db: AsyncSession, user_id: int) -> UserResponse:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User not found")
    return UserResponse.model_validate(user)


async def get_users(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    role: UserRole | None = None,
) -> UserListResponse:
    query = select(User)
    count_query = select(func.count(User.id))

    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)

    result = await db.execute(count_query)
    total = result.scalar() or 0

    offset = (page - 1) * limit
    result = await db.execute(query.offset(offset).limit(limit))
    users = result.scalars().all()

    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        limit=limit,
    )


async def update_user(db: AsyncSession, user_id: int, data: UserUpdate) -> UserResponse:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    return UserResponse.model_validate(user)


async def deactivate_user(db: AsyncSession, user_id: int) -> None:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User not found")

    user.is_active = False
    await db.flush()
