from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.models.org import Organization, OrganizationMember, OrganizationPlan
from src.schemas.org import (
    OrganizationCreate,
    OrganizationMemberCreate,
    OrganizationMemberResponse,
    OrganizationPlanCreate,
    OrganizationPlanResponse,
    OrganizationResponse,
    OrganizationUpdate,
)


async def create_org(db: AsyncSession, data: OrganizationCreate) -> OrganizationResponse:
    org = Organization(**data.model_dump())
    db.add(org)
    await db.flush()
    await db.refresh(org)
    return OrganizationResponse.model_validate(org)


async def update_org(db: AsyncSession, org_id: int, data: OrganizationUpdate) -> OrganizationResponse:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise NotFoundError("Organization not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(org, k, v)
    await db.flush()
    await db.refresh(org)
    return OrganizationResponse.model_validate(org)


async def list_orgs(db: AsyncSession) -> list[OrganizationResponse]:
    result = await db.execute(select(Organization))
    orgs = result.scalars().all()
    return [OrganizationResponse.model_validate(o) for o in orgs]


async def create_plan(
    db: AsyncSession, org_id: int, data: OrganizationPlanCreate
) -> OrganizationPlanResponse:
    plan = OrganizationPlan(organization_id=org_id, **data.model_dump())
    db.add(plan)
    await db.flush()
    await db.refresh(plan)
    return OrganizationPlanResponse.model_validate(plan)


async def list_plans(db: AsyncSession, org_id: int) -> list[OrganizationPlanResponse]:
    result = await db.execute(
        select(OrganizationPlan).where(OrganizationPlan.organization_id == org_id)
    )
    plans = result.scalars().all()
    return [OrganizationPlanResponse.model_validate(p) for p in plans]


async def add_member(
    db: AsyncSession, org_id: int, data: OrganizationMemberCreate
) -> OrganizationMemberResponse:
    member = OrganizationMember(organization_id=org_id, **data.model_dump())
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return OrganizationMemberResponse.model_validate(member)


async def list_members(db: AsyncSession, org_id: int) -> list[OrganizationMemberResponse]:
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.organization_id == org_id)
    )
    members = result.scalars().all()
    return [OrganizationMemberResponse.model_validate(m) for m in members]


async def set_plan(db: AsyncSession, org_id: int, plan_id: int) -> OrganizationResponse:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise NotFoundError("Organization not found")
    org.billing_plan_id = plan_id
    await db.flush()
    await db.refresh(org)
    return OrganizationResponse.model_validate(org)
