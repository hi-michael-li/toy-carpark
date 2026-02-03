import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import NotFoundError, ValidationError
from src.models.ev_charging import EVChargingStation
from src.models.parking import ParkingSpace, Zone
from src.models.session import ParkingSession
from src.models.vehicle import Vehicle, VehicleType
from src.schemas.session import (
    FeeCalculation,
    SessionEntryRequest,
    SessionEntryResponse,
    SessionExitRequest,
    SessionExitResponse,
    SessionListResponse,
    SessionResponse,
)
from src.services import parking as parking_service
from src.services import payment as payment_service
from src.services import vehicle as vehicle_service
from src.utils.constants import ChargerType, SessionStatus, SpaceStatus


def generate_ticket_number() -> str:
    return f"TKT-{uuid.uuid4().hex[:12].upper()}"


async def create_entry(db: AsyncSession, data: SessionEntryRequest) -> SessionEntryResponse:
    vehicle_response = await vehicle_service.get_vehicle_by_plate(db, data.license_plate)

    if not vehicle_response:
        result = await db.execute(select(VehicleType).limit(1))
        default_type = result.scalar_one_or_none()
        if not default_type:
            default_type = VehicleType(name="Car", size_category="medium")
            db.add(default_type)
            await db.flush()

        vehicle = Vehicle(
            license_plate=data.license_plate.upper(),
            vehicle_type_id=default_type.id,
        )
        db.add(vehicle)
        await db.flush()
        vehicle_id = vehicle.id
    else:
        vehicle_id = vehicle_response.id

        # Check for existing active session for this vehicle
        result = await db.execute(
            select(ParkingSession).where(
                ParkingSession.vehicle_id == vehicle_id,
                ParkingSession.status == SessionStatus.ACTIVE,
            )
        )
        existing_session = result.scalar_one_or_none()
        if existing_session:
            raise ValidationError(
                f"Vehicle already has an active parking session "
                f"(ticket: {existing_session.ticket_number})"
            )

    available_spaces = await parking_service.get_available_spaces(db, limit=1)
    space_id = available_spaces[0].id if available_spaces else None

    session = ParkingSession(
        vehicle_id=vehicle_id,
        space_id=space_id,
        entry_time=datetime.now(UTC),
        ticket_number=generate_ticket_number(),
        status=SessionStatus.ACTIVE,
        entry_gate=data.entry_gate,
        lpr_entry_image=data.lpr_image,
    )
    db.add(session)

    if space_id:
        result = await db.execute(select(ParkingSpace).where(ParkingSpace.id == space_id))
        space = result.scalar_one()
        space.status = SpaceStatus.OCCUPIED

    await db.flush()

    result = await db.execute(
        select(ParkingSession)
        .where(ParkingSession.id == session.id)
        .options(
            selectinload(ParkingSession.vehicle).selectinload(Vehicle.vehicle_type),
            selectinload(ParkingSession.space).selectinload(ParkingSpace.zone).selectinload(Zone.level),
        )
    )
    session = result.scalar_one()

    session_response = SessionResponse.model_validate(session)
    space_response = None
    if session.space:
        from src.schemas.parking import ParkingSpaceResponse

        space_response = ParkingSpaceResponse.model_validate(session.space)

    return SessionEntryResponse(
        session=session_response,
        ticket_number=session.ticket_number,
        space_assigned=space_response,
    )


async def process_exit(db: AsyncSession, data: SessionExitRequest) -> SessionExitResponse:
    query = select(ParkingSession).options(
        selectinload(ParkingSession.vehicle).selectinload(Vehicle.vehicle_type),
        selectinload(ParkingSession.space).selectinload(ParkingSpace.zone).selectinload(Zone.level),
    )

    if data.ticket_number:
        query = query.where(
            ParkingSession.ticket_number == data.ticket_number,
            ParkingSession.status == SessionStatus.ACTIVE,
        )
    elif data.license_plate:
        query = query.join(Vehicle).where(
            Vehicle.license_plate == data.license_plate.upper(),
            ParkingSession.status == SessionStatus.ACTIVE,
        )
    else:
        raise ValidationError("Either ticket_number or license_plate is required")

    result = await db.execute(query)
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError("Active session not found")

    exit_time = datetime.now(UTC)
    session.exit_time = exit_time
    session.exit_gate = data.exit_gate

    if session.space_id:
        result = await db.execute(select(ParkingSpace).where(ParkingSpace.id == session.space_id))
        space = result.scalar_one()
        space.status = SpaceStatus.AVAILABLE

    fee_calc = await calculate_fee(db, session.id)
    entry_time = session.entry_time
    if exit_time.tzinfo is not None and entry_time.tzinfo is None:
        entry_time = entry_time.replace(tzinfo=UTC)
    duration_minutes = int((exit_time - entry_time).total_seconds() / 60)

    await db.flush()

    result = await db.execute(
        select(ParkingSession)
        .where(ParkingSession.id == session.id)
        .options(
            selectinload(ParkingSession.vehicle).selectinload(Vehicle.vehicle_type),
            selectinload(ParkingSession.space).selectinload(ParkingSpace.zone).selectinload(Zone.level),
        )
    )
    session = result.scalar_one()

    return SessionExitResponse(
        session=SessionResponse.model_validate(session),
        payment_due=fee_calc.total,
        duration_minutes=duration_minutes,
    )


async def complete_session(db: AsyncSession, session_id: int) -> SessionResponse:
    result = await db.execute(
        select(ParkingSession)
        .where(ParkingSession.id == session_id)
        .options(
            selectinload(ParkingSession.vehicle).selectinload(Vehicle.vehicle_type),
            selectinload(ParkingSession.space).selectinload(ParkingSpace.zone).selectinload(Zone.level),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError("Session not found")

    session.status = SessionStatus.COMPLETED
    await db.flush()
    await db.refresh(session)

    return SessionResponse.model_validate(session)


async def get_active_sessions(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    zone_id: int | None = None,
) -> SessionListResponse:
    query = (
        select(ParkingSession)
        .where(ParkingSession.status == SessionStatus.ACTIVE)
        .options(
            selectinload(ParkingSession.vehicle).selectinload(Vehicle.vehicle_type),
            selectinload(ParkingSession.space).selectinload(ParkingSpace.zone).selectinload(Zone.level),
        )
    )
    count_query = select(func.count(ParkingSession.id)).where(
        ParkingSession.status == SessionStatus.ACTIVE
    )

    if zone_id:
        query = query.join(ParkingSpace).where(ParkingSpace.zone_id == zone_id)
        count_query = count_query.join(ParkingSpace).where(ParkingSpace.zone_id == zone_id)

    result = await db.execute(count_query)
    total = result.scalar() or 0

    offset = (page - 1) * limit
    result = await db.execute(query.offset(offset).limit(limit))
    sessions = result.scalars().all()

    return SessionListResponse(
        sessions=[SessionResponse.model_validate(s) for s in sessions],
        total=total,
        page=page,
        limit=limit,
    )


async def get_session_by_id(db: AsyncSession, session_id: int) -> SessionResponse:
    result = await db.execute(
        select(ParkingSession)
        .where(ParkingSession.id == session_id)
        .options(
            selectinload(ParkingSession.vehicle).selectinload(Vehicle.vehicle_type),
            selectinload(ParkingSession.space).selectinload(ParkingSpace.zone).selectinload(Zone.level),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError("Session not found")
    return SessionResponse.model_validate(session)


async def get_session_by_ticket(db: AsyncSession, ticket_number: str) -> SessionResponse:
    result = await db.execute(
        select(ParkingSession)
        .where(ParkingSession.ticket_number == ticket_number)
        .options(
            selectinload(ParkingSession.vehicle).selectinload(Vehicle.vehicle_type),
            selectinload(ParkingSession.space).selectinload(ParkingSpace.zone).selectinload(Zone.level),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError("Session not found")
    return SessionResponse.model_validate(session)


async def calculate_fee(
    db: AsyncSession, session_id: int, exit_time: datetime | None = None
) -> FeeCalculation:
    result = await db.execute(
        select(ParkingSession)
        .where(ParkingSession.id == session_id)
        .options(
            selectinload(ParkingSession.vehicle),
            selectinload(ParkingSession.space),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError("Session not found")

    end_time = exit_time or session.exit_time or datetime.now(UTC)
    entry_time = session.entry_time
    # Handle timezone-aware/naive datetime comparison
    if end_time.tzinfo is not None and entry_time.tzinfo is None:
        entry_time = entry_time.replace(tzinfo=UTC)
    elif end_time.tzinfo is None and entry_time.tzinfo is not None:
        end_time = end_time.replace(tzinfo=UTC)
    duration = end_time - entry_time
    duration_minutes = int(duration.total_seconds() / 60)

    # Get both hourly and daily rates
    vehicle_type_id = session.vehicle.vehicle_type_id if session.vehicle else None
    zone_id = session.space.zone_id if session.space else None
    rates = await payment_service.get_applicable_rates(db, vehicle_type_id, zone_id)
    hourly_rate = rates.get("hourly")
    daily_rate = rates.get("daily")

    # Check grace period
    grace_period = hourly_rate.grace_period_minutes if hourly_rate else None
    if grace_period and duration_minutes <= grace_period:
        return FeeCalculation(
            session_id=session_id,
            duration_minutes=duration_minutes,
            base_fee=0,
            discounts=0,
            tax=0,
            total=0,
            breakdown=[{"description": "Within grace period", "amount": 0}],
        )

    # Calculate base hourly fee
    base_hourly_amount = float(hourly_rate.amount) if hourly_rate else 5.0
    hours = max(1, (duration_minutes + 59) // 60)
    breakdown = []

    # Check for peak pricing
    peak_multiplier = 1.0
    is_peak = False
    if hourly_rate and hourly_rate.peak_start_time and hourly_rate.peak_end_time:
        current_time = end_time.time()
        peak_start = hourly_rate.peak_start_time
        peak_end = hourly_rate.peak_end_time

        # Handle peak hours that span midnight
        if peak_start <= peak_end:
            is_peak = peak_start <= current_time <= peak_end
        else:
            is_peak = current_time >= peak_start or current_time <= peak_end

        if is_peak and hourly_rate.peak_multiplier:
            peak_multiplier = hourly_rate.peak_multiplier

    # Calculate fee with peak pricing
    effective_hourly_rate = base_hourly_amount * peak_multiplier
    base_fee = effective_hourly_rate * hours

    if is_peak and peak_multiplier != 1.0:
        breakdown.append({
            "description": f"Parking ({hours} hour(s) @ ${base_hourly_amount}/hr)",
            "amount": base_hourly_amount * hours,
        })
        breakdown.append({
            "description": f"Peak hour surcharge ({(peak_multiplier - 1) * 100:.0f}%)",
            "amount": (effective_hourly_rate - base_hourly_amount) * hours,
        })
    else:
        breakdown.append({
            "description": f"Parking ({hours} hour(s) @ ${effective_hourly_rate}/hr)",
            "amount": base_fee,
        })

    total_fee = base_fee

    ev_hourly_rate = None
    if session.space and session.space.is_ev_charging:
        result = await db.execute(
            select(EVChargingStation).where(EVChargingStation.space_id == session.space_id)
        )
        station = result.scalar_one_or_none()
        if station:
            ev_rate = float(station.price_per_kwh)
            if station.charger_type == ChargerType.LEVEL2:
                ev_rate = ev_rate + 0.25
            ev_hourly_rate = ev_rate * float(station.power_kw) * 0.8

    # Apply daily maximum cap if available
    if daily_rate:
        daily_max = float(daily_rate.amount)
        if ev_hourly_rate is not None:
            extra = (ev_hourly_rate - effective_hourly_rate) * hours
            if extra > 0:
                daily_max = daily_max + extra
        full_days = duration_minutes // (24 * 60)
        remaining_minutes = duration_minutes % (24 * 60)

        if full_days > 0:
            # Calculate fee for full days at daily rate
            daily_fee = daily_max * full_days
            if remaining_minutes > 0:
                remaining_hours = max(1, (remaining_minutes + 59) // 60)
            else:
                remaining_hours = 0
            if remaining_hours > 0:
                remaining_fee = min(effective_hourly_rate * remaining_hours, daily_max)
            else:
                remaining_fee = 0
            capped_total = daily_fee + remaining_fee

            if capped_total < total_fee:
                total_fee = capped_total
                breakdown = [
                    {
                        "description": f"Daily rate ({full_days} day(s) @ ${daily_max}/day)",
                        "amount": daily_fee,
                    },
                ]
                if remaining_fee > 0:
                    breakdown.append({
                        "description": f"Remaining time ({remaining_hours} hour(s))",
                        "amount": remaining_fee,
                    })
        elif total_fee > daily_max:
            # Single day but exceeds daily cap
            total_fee = daily_max
            breakdown = [
                {
                    "description": f"Daily maximum cap applied (was ${base_fee:.2f})",
                    "amount": daily_max,
                },
            ]

    return FeeCalculation(
        session_id=session_id,
        duration_minutes=duration_minutes,
        base_fee=base_fee,
        discounts=0,
        tax=0,
        total=round(total_fee, 2),
        breakdown=breakdown,
    )


async def assign_space(db: AsyncSession, session_id: int, space_id: int) -> SessionResponse:
    result = await db.execute(
        select(ParkingSession)
        .where(ParkingSession.id == session_id)
        .options(
            selectinload(ParkingSession.vehicle).selectinload(Vehicle.vehicle_type),
            selectinload(ParkingSession.space).selectinload(ParkingSpace.zone).selectinload(Zone.level),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError("Session not found")

    result = await db.execute(select(ParkingSpace).where(ParkingSpace.id == space_id))
    space = result.scalar_one_or_none()
    if not space:
        raise NotFoundError("Space not found")
    if space.status != SpaceStatus.AVAILABLE:
        raise ValidationError("Space is not available")

    if session.space_id:
        result = await db.execute(select(ParkingSpace).where(ParkingSpace.id == session.space_id))
        old_space = result.scalar_one()
        old_space.status = SpaceStatus.AVAILABLE

    session.space_id = space_id
    space.status = SpaceStatus.OCCUPIED

    await db.flush()

    # Expire all objects so they get reloaded fresh with updated timestamps
    db.expire_all()

    # Re-fetch with eager loading to avoid lazy loading issues
    result = await db.execute(
        select(ParkingSession)
        .where(ParkingSession.id == session_id)
        .options(
            selectinload(ParkingSession.vehicle).selectinload(Vehicle.vehicle_type),
            selectinload(ParkingSession.space).selectinload(ParkingSpace.zone).selectinload(Zone.level),
        )
    )
    session = result.scalar_one()

    return SessionResponse.model_validate(session)
