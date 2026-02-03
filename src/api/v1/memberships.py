from fastapi import APIRouter, Query

from src.core.dependencies import DB, ActiveUser, AdminUser, Pagination
from src.core.exceptions import AuthorizationError
from src.schemas.membership import (
    MembershipCreate,
    MembershipListResponse,
    MembershipPlanCreate,
    MembershipPlanResponse,
    MembershipPlanUpdate,
    MembershipResponse,
    MembershipSubscribeResponse,
    MembershipUsageStats,
)
from src.services import membership as membership_service
from src.utils.constants import MembershipStatus, UserRole

router = APIRouter(prefix="/memberships", tags=["Memberships"])


# Plans
@router.get("/plans", response_model=list[MembershipPlanResponse])
async def list_membership_plans(db: DB, is_active: bool = Query(True)):
    return await membership_service.get_membership_plans(db, is_active)


@router.post("/plans", response_model=MembershipPlanResponse)
async def create_membership_plan(db: DB, admin: AdminUser, data: MembershipPlanCreate):
    return await membership_service.create_membership_plan(db, data)


@router.put("/plans/{plan_id}", response_model=MembershipPlanResponse)
async def update_membership_plan(
    db: DB, admin: AdminUser, plan_id: int, data: MembershipPlanUpdate
):
    return await membership_service.update_membership_plan(db, plan_id, data)


# Memberships
@router.post("", response_model=MembershipSubscribeResponse)
async def subscribe_to_membership(db: DB, user: ActiveUser, data: MembershipCreate):
    return await membership_service.subscribe_to_plan(db, user.id, data)


@router.get("", response_model=MembershipListResponse)
async def list_memberships(
    db: DB,
    user: ActiveUser,
    pagination: Pagination,
    status: MembershipStatus | None = Query(None),
):
    return await membership_service.get_memberships(
        db, pagination.page, pagination.limit, user.id, status
    )


@router.get("/{membership_id}", response_model=MembershipResponse)
async def get_membership(db: DB, user: ActiveUser, membership_id: int):
    membership = await membership_service.get_membership_by_id(db, membership_id)
    if user.role != UserRole.ADMIN and membership.user_id != user.id:
        raise AuthorizationError("Not allowed to access this membership")
    return membership


@router.get("/{membership_id}/usage", response_model=MembershipUsageStats)
async def get_membership_usage(db: DB, user: ActiveUser, membership_id: int):
    membership = await membership_service.get_membership_by_id(db, membership_id)
    if user.role != UserRole.ADMIN and membership.user_id != user.id:
        raise AuthorizationError("Not allowed to access this membership")
    return await membership_service.get_membership_usage(db, membership_id)


@router.post("/{membership_id}/cancel", response_model=MembershipResponse)
async def cancel_membership(db: DB, user: ActiveUser, membership_id: int):
    membership = await membership_service.get_membership_by_id(db, membership_id)
    if user.role != UserRole.ADMIN and membership.user_id != user.id:
        raise AuthorizationError("Not allowed to cancel this membership")
    return await membership_service.cancel_membership(db, membership_id)


@router.post("/{membership_id}/renew", response_model=MembershipSubscribeResponse)
async def renew_membership(db: DB, user: ActiveUser, membership_id: int):
    membership = await membership_service.get_membership_by_id(db, membership_id)
    if user.role != UserRole.ADMIN and membership.user_id != user.id:
        raise AuthorizationError("Not allowed to renew this membership")
    return await membership_service.renew_membership(db, membership_id)
