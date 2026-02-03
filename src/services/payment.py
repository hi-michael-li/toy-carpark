import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError, PaymentError
from src.models.payment import Discount, Payment, Rate
from src.models.session import ParkingSession
from src.schemas.payment import (
    DiscountCreate,
    DiscountResponse,
    DiscountUpdate,
    DiscountValidationResponse,
    PaymentCreate,
    PaymentListResponse,
    PaymentResponse,
    RateCreate,
    RateResponse,
    RateUpdate,
    ValidateExitResponse,
)
from src.services import session as session_service
from src.utils.constants import DiscountType, PaymentStatus, RateType


def generate_receipt_number() -> str:
    return f"RCP-{uuid.uuid4().hex[:12].upper()}"


async def get_rates(
    db: AsyncSession,
    vehicle_type_id: int | None = None,
    zone_id: int | None = None,
    is_active: bool | None = True,
) -> list[RateResponse]:
    query = select(Rate)
    if vehicle_type_id:
        query = query.where(Rate.vehicle_type_id == vehicle_type_id)
    if zone_id:
        query = query.where(Rate.zone_id == zone_id)
    if is_active is not None:
        query = query.where(Rate.is_active == is_active)

    result = await db.execute(query)
    rates = result.scalars().all()
    return [RateResponse.model_validate(r) for r in rates]


async def create_rate(db: AsyncSession, data: RateCreate) -> RateResponse:
    rate = Rate(**data.model_dump())
    db.add(rate)
    await db.flush()
    await db.refresh(rate)
    return RateResponse.model_validate(rate)


async def update_rate(db: AsyncSession, rate_id: int, data: RateUpdate) -> RateResponse:
    result = await db.execute(select(Rate).where(Rate.id == rate_id))
    rate = result.scalar_one_or_none()
    if not rate:
        raise NotFoundError("Rate not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rate, field, value)

    await db.flush()
    await db.refresh(rate)
    return RateResponse.model_validate(rate)


async def get_applicable_rate(
    db: AsyncSession,
    vehicle_type_id: int | None = None,
    zone_id: int | None = None,
    rate_type: RateType = RateType.HOURLY,
) -> Rate | None:
    """
    Find the most applicable rate using priority matching:
    1. Exact match (both vehicle_type AND zone)
    2. Vehicle type only match
    3. Zone only match
    4. Generic rate (no vehicle_type or zone)
    """
    now = datetime.now(UTC)
    base_query = (
        select(Rate)
        .where(
            Rate.is_active == True,  # noqa: E712
            Rate.effective_from <= now,
            or_(Rate.effective_to.is_(None), Rate.effective_to >= now),
            Rate.rate_type == rate_type,
        )
        .order_by(Rate.effective_from.desc())
    )

    # Priority 1: Exact match (both vehicle_type AND zone)
    if vehicle_type_id and zone_id:
        result = await db.execute(
            base_query.where(
                Rate.vehicle_type_id == vehicle_type_id,
                Rate.zone_id == zone_id,
            ).limit(1)
        )
        rate = result.scalar_one_or_none()
        if rate:
            return rate

    # Priority 2: Vehicle type only (no zone restriction)
    if vehicle_type_id:
        result = await db.execute(
            base_query.where(
                Rate.vehicle_type_id == vehicle_type_id,
                Rate.zone_id.is_(None),
            ).limit(1)
        )
        rate = result.scalar_one_or_none()
        if rate:
            return rate

    # Priority 3: Zone only (no vehicle type restriction)
    if zone_id:
        result = await db.execute(
            base_query.where(
                Rate.vehicle_type_id.is_(None),
                Rate.zone_id == zone_id,
            ).limit(1)
        )
        rate = result.scalar_one_or_none()
        if rate:
            return rate

    # Priority 4: Generic rate (no restrictions)
    result = await db.execute(
        base_query.where(
            Rate.vehicle_type_id.is_(None),
            Rate.zone_id.is_(None),
        ).limit(1)
    )
    return result.scalar_one_or_none()


async def get_applicable_rates(
    db: AsyncSession,
    vehicle_type_id: int | None = None,
    zone_id: int | None = None,
) -> dict[str, Rate | None]:
    """
    Get both hourly and daily rates for fee calculation.
    Returns dict with 'hourly' and 'daily' keys.
    """
    hourly_rate = await get_applicable_rate(db, vehicle_type_id, zone_id, RateType.HOURLY)
    daily_rate = await get_applicable_rate(db, vehicle_type_id, zone_id, RateType.DAILY)
    return {"hourly": hourly_rate, "daily": daily_rate}


async def get_discounts(
    db: AsyncSession,
    is_active: bool | None = True,
    partner_name: str | None = None,
) -> list[DiscountResponse]:
    query = select(Discount)
    if is_active is not None:
        query = query.where(Discount.is_active == is_active)
    if partner_name:
        query = query.where(Discount.partner_name.ilike(f"%{partner_name}%"))

    result = await db.execute(query)
    discounts = result.scalars().all()
    return [DiscountResponse.model_validate(d) for d in discounts]


async def create_discount(db: AsyncSession, data: DiscountCreate) -> DiscountResponse:
    discount = Discount(**data.model_dump())
    db.add(discount)
    await db.flush()
    await db.refresh(discount)
    return DiscountResponse.model_validate(discount)


async def update_discount(
    db: AsyncSession, discount_id: int, data: DiscountUpdate
) -> DiscountResponse:
    result = await db.execute(select(Discount).where(Discount.id == discount_id))
    discount = result.scalar_one_or_none()
    if not discount:
        raise NotFoundError("Discount not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(discount, field, value)

    await db.flush()
    await db.refresh(discount)
    return DiscountResponse.model_validate(discount)


async def validate_discount(
    db: AsyncSession, code: str, session_id: int | None = None
) -> DiscountValidationResponse:
    result = await db.execute(select(Discount).where(Discount.code == code.upper()))
    discount = result.scalar_one_or_none()

    if not discount:
        return DiscountValidationResponse(is_valid=False, message="Invalid discount code")

    now = datetime.now(UTC)
    if not discount.is_active:
        return DiscountValidationResponse(is_valid=False, message="Discount is not active")

    valid_from = discount.valid_from
    valid_to = discount.valid_to
    if valid_from.tzinfo is None:
        valid_from = valid_from.replace(tzinfo=UTC)
    if valid_to.tzinfo is None:
        valid_to = valid_to.replace(tzinfo=UTC)

    if valid_from > now:
        return DiscountValidationResponse(is_valid=False, message="Discount is not yet valid")
    if valid_to < now:
        return DiscountValidationResponse(is_valid=False, message="Discount has expired")
    if discount.max_uses and discount.current_uses >= discount.max_uses:
        return DiscountValidationResponse(is_valid=False, message="Discount usage limit reached")

    discount_amount = None
    if session_id:
        fee_calc = await session_service.calculate_fee(db, session_id)
        if discount.discount_type == DiscountType.PERCENTAGE:
            discount_amount = fee_calc.total * (float(discount.value) / 100)
        elif discount.discount_type == DiscountType.FIXED_AMOUNT:
            discount_amount = min(float(discount.value), fee_calc.total)

    return DiscountValidationResponse(
        is_valid=True,
        discount=DiscountResponse.model_validate(discount),
        discount_amount=discount_amount,
    )


async def process_payment(
    db: AsyncSession, data: PaymentCreate, user_id: int | None = None
) -> PaymentResponse:
    result = await db.execute(
        select(ParkingSession).where(ParkingSession.id == data.session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError("Session not found")

    result = await db.execute(
        select(Payment).where(
            Payment.session_id == data.session_id, Payment.status == PaymentStatus.COMPLETED
        )
    )
    if result.scalar_one_or_none():
        raise PaymentError("Session has already been paid")

    fee_calc = await session_service.calculate_fee(db, data.session_id)

    discount_id = None
    discount_amount = 0.0
    if data.discount_code:
        validation = await validate_discount(db, data.discount_code, data.session_id)
        if validation.is_valid and validation.discount:
            discount_id = validation.discount.id
            discount_amount = validation.discount_amount or 0

            result = await db.execute(select(Discount).where(Discount.id == discount_id))
            discount = result.scalar_one()
            discount.current_uses += 1

    total_amount = max(0, fee_calc.total - discount_amount)

    if data.amount < total_amount:
        raise PaymentError(f"Insufficient payment amount. Required: ${total_amount:.2f}")

    payment = Payment(
        session_id=data.session_id,
        user_id=user_id,
        amount=fee_calc.total,
        payment_method=data.payment_method,
        status=PaymentStatus.COMPLETED,
        discount_id=discount_id,
        discount_amount=discount_amount,
        tax_amount=0,
        total_amount=total_amount,
        receipt_number=generate_receipt_number(),
        paid_at=datetime.now(UTC),
    )
    db.add(payment)
    await db.flush()
    await db.refresh(payment)

    return PaymentResponse.model_validate(payment)


async def get_payments(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    status: PaymentStatus | None = None,
) -> PaymentListResponse:
    query = select(Payment)
    count_query = select(func.count(Payment.id))
    sum_query = select(func.sum(Payment.total_amount))

    if status:
        query = query.where(Payment.status == status)
        count_query = count_query.where(Payment.status == status)
        sum_query = sum_query.where(Payment.status == status)

    result = await db.execute(count_query)
    total = result.scalar() or 0

    result = await db.execute(sum_query)
    total_amount = result.scalar() or 0

    offset = (page - 1) * limit
    result = await db.execute(query.offset(offset).limit(limit))
    payments = result.scalars().all()

    return PaymentListResponse(
        payments=[PaymentResponse.model_validate(p) for p in payments],
        total=total,
        total_amount=float(total_amount),
        page=page,
        limit=limit,
    )


async def validate_exit(db: AsyncSession, ticket_number: str) -> ValidateExitResponse:
    result = await db.execute(
        select(ParkingSession).where(ParkingSession.ticket_number == ticket_number)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError("Session not found")

    result = await db.execute(
        select(Payment).where(
            Payment.session_id == session.id, Payment.status == PaymentStatus.COMPLETED
        )
    )
    payment = result.scalar_one_or_none()

    is_paid = payment is not None

    if is_paid:
        return ValidateExitResponse(
            is_paid=True,
            can_exit=True,
            time_remaining_minutes=15,
        )

    fee_calc = await session_service.calculate_fee(db, session.id)
    return ValidateExitResponse(
        is_paid=False,
        can_exit=False,
        amount_due=fee_calc.total,
    )
