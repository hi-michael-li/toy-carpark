from fastapi import APIRouter, Query

from src.core.dependencies import ActiveUser, AdminUser, DB
from src.schemas.org import (
    OrganizationCreate,
    OrganizationMemberCreate,
    OrganizationMemberResponse,
    OrganizationPlanCreate,
    OrganizationPlanResponse,
    OrganizationResponse,
    OrganizationUpdate,
)
from src.services import org as org_service

router = APIRouter(prefix="/orgs", tags=["Organizations"])


@router.get("", response_model=list[OrganizationResponse])
async def list_orgs(db: DB, user: ActiveUser):
    return await org_service.list_orgs(db)


@router.post("", response_model=OrganizationResponse)
async def create_org(db: DB, admin: AdminUser, data: OrganizationCreate):
    return await org_service.create_org(db, data)


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_org(db: DB, admin: AdminUser, org_id: int, data: OrganizationUpdate):
    return await org_service.update_org(db, org_id, data)


@router.post("/{org_id}/members", response_model=OrganizationMemberResponse)
async def add_member(
    db: DB,
    user: ActiveUser,
    org_id: int,
    user_id: int | None = Query(None),
    role: str | None = Query(None),
    is_primary: bool = Query(False),
):
    data = OrganizationMemberCreate(user_id=user_id or user.id, role=role, is_primary=is_primary)
    return await org_service.add_member(db, org_id, data)


@router.get("/{org_id}/members", response_model=list[OrganizationMemberResponse])
async def list_members(db: DB, user: ActiveUser, org_id: int):
    return await org_service.list_members(db, org_id)


@router.post("/{org_id}/plans", response_model=OrganizationPlanResponse)
async def create_plan(db: DB, admin: AdminUser, org_id: int, data: OrganizationPlanCreate):
    return await org_service.create_plan(db, org_id, data)


@router.get("/{org_id}/plans", response_model=list[OrganizationPlanResponse])
async def list_plans(db: DB, user: ActiveUser, org_id: int):
    return await org_service.list_plans(db, org_id)


@router.post("/{org_id}/set-plan", response_model=OrganizationResponse)
async def set_plan(
    db: DB,
    admin: AdminUser,
    org_id: int,
    plan_id: int = Query(...),
):
    return await org_service.set_plan(db, org_id, plan_id)
