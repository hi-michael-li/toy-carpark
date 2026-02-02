from fastapi import APIRouter, Query

from src.core.dependencies import DB, AdminUser, Pagination
from src.schemas.common import MessageResponse
from src.schemas.user import UserListResponse, UserResponse, UserUpdate
from src.services import user as user_service
from src.utils.constants import UserRole

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    db: DB,
    admin: AdminUser,
    pagination: Pagination,
    role: UserRole | None = Query(None),
):
    return await user_service.get_users(db, pagination.page, pagination.limit, role)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(db: DB, admin: AdminUser, user_id: int):
    return await user_service.get_user_by_id(db, user_id)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(db: DB, admin: AdminUser, user_id: int, data: UserUpdate):
    return await user_service.update_user(db, user_id, data)


@router.delete("/{user_id}", response_model=MessageResponse)
async def deactivate_user(db: DB, admin: AdminUser, user_id: int):
    await user_service.deactivate_user(db, user_id)
    return MessageResponse(message="User deactivated successfully")
