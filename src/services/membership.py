from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ConflictError, NotFoundError, ValidationError
from src.models.membership import Membership, MembershipPlan
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
from src.utils.constants import MembershipStatus


async def get_membership_plans(
    db: AsyncSession, is_active: bool = True
) -> list[MembershipPlanResponse]:
    query = select(MembershipPlan)
    if is_active is not None:
        query = query.where(MembershipPlan.is_active == is_active)
    result = await db.execute(query)
    plans = result.scalars().all()
    return [MembershipPlanResponse.model_validate(p) for p in plans]


async def create_membership_plan(
    db: AsyncSession, data: MembershipPlanCreate
) -> MembershipPlanResponse:
    plan = MembershipPlan(**data.model_dump())
    db.add(plan)
    await db.flush()
    await db.refresh(plan)
    return MembershipPlanResponse.model_validate(plan)


async def update_membership_plan(
    db: AsyncSession, plan_id: int, data: MembershipPlanUpdate
) -> MembershipPlanResponse:
    result = await db.execute(select(MembershipPlan).where(MembershipPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise NotFoundError("Membership plan not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)

    await db.flush()
    await db.refresh(plan)
    return MembershipPlanResponse.model_validate(plan)


async def subscribe_to_plan(
    db: AsyncSession, user_id: int, data: MembershipCreate
) -> MembershipSubscribeResponse:
    result = await db.execute(select(MembershipPlan).where(MembershipPlan.id == data.plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise NotFoundError("Membership plan not found")
    if not plan.is_active:
        raise ValidationError("Membership plan is not available")

    result = await db.execute(
        select(Membership).where(
            Membership.user_id == user_id, Membership.status == MembershipStatus.ACTIVE
        )
    )
    if result.scalar_one_or_none():
        raise ConflictError("User already has an active membership")

    start_date = date.today()
    end_date = start_date + relativedelta(months=plan.duration_months)

    membership = Membership(
        user_id=user_id,
        plan_id=data.plan_id,
        start_date=start_date,
        end_date=end_date,
        status=MembershipStatus.ACTIVE,
        auto_renew=data.auto_renew,
    )
    db.add(membership)
    await db.flush()

    result = await db.execute(
        select(Membership)
        .where(Membership.id == membership.id)
        .options(selectinload(Membership.plan))
    )
    membership = result.scalar_one()

    return MembershipSubscribeResponse(
        membership=MembershipResponse.model_validate(membership),
        payment_id=0,
    )


async def get_memberships(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    user_id: int | None = None,
    status: MembershipStatus | None = None,
) -> MembershipListResponse:
    query = select(Membership).options(selectinload(Membership.plan))
    count_query = select(func.count(Membership.id))

    if user_id:
        query = query.where(Membership.user_id == user_id)
        count_query = count_query.where(Membership.user_id == user_id)
    if status:
        query = query.where(Membership.status == status)
        count_query = count_query.where(Membership.status == status)

    result = await db.execute(count_query)
    total = result.scalar() or 0

    offset = (page - 1) * limit
    result = await db.execute(query.offset(offset).limit(limit))
    memberships = result.scalars().all()

    return MembershipListResponse(
        memberships=[MembershipResponse.model_validate(m) for m in memberships],
        total=total,
        page=page,
        limit=limit,
    )


async def get_membership_by_id(db: AsyncSession, membership_id: int) -> MembershipResponse:
    result = await db.execute(
        select(Membership)
        .where(Membership.id == membership_id)
        .options(selectinload(Membership.plan))
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise NotFoundError("Membership not found")
    return MembershipResponse.model_validate(membership)


async def get_membership_usage(db: AsyncSession, membership_id: int) -> MembershipUsageStats:
    result = await db.execute(
        select(Membership)
        .where(Membership.id == membership_id)
        .options(selectinload(Membership.plan))
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise NotFoundError("Membership not found")

    included_hours = membership.plan.included_hours if membership.plan else None
    remaining_hours = None
    if included_hours:
        remaining_hours = max(0, included_hours - membership.used_hours)

    days_remaining = (membership.end_date - date.today()).days

    return MembershipUsageStats(
        membership_id=membership_id,
        included_hours=included_hours,
        used_hours=membership.used_hours,
        remaining_hours=remaining_hours,
        days_remaining=max(0, days_remaining),
    )


async def cancel_membership(
    db: AsyncSession, membership_id: int, reason: str | None = None
) -> MembershipResponse:
    result = await db.execute(
        select(Membership)
        .where(Membership.id == membership_id)
        .options(selectinload(Membership.plan))
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise NotFoundError("Membership not found")

    if membership.status != MembershipStatus.ACTIVE:
        raise ValidationError("Membership is not active")

    membership.status = MembershipStatus.CANCELLED
    await db.flush()
    await db.refresh(membership)

    return MembershipResponse.model_validate(membership)


async def renew_membership(db: AsyncSession, membership_id: int) -> MembershipSubscribeResponse:
    result = await db.execute(
        select(Membership)
        .where(Membership.id == membership_id)
        .options(selectinload(Membership.plan))
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise NotFoundError("Membership not found")

    if membership.status == MembershipStatus.ACTIVE:
        membership.end_date = membership.end_date + relativedelta(
            months=membership.plan.duration_months
        )
    else:
        membership.start_date = date.today()
        membership.end_date = date.today() + relativedelta(months=membership.plan.duration_months)
        membership.status = MembershipStatus.ACTIVE
        membership.used_hours = 0

    await db.flush()
    await db.refresh(membership)

    return MembershipSubscribeResponse(
        membership=MembershipResponse.model_validate(membership),
        payment_id=0,
    )
