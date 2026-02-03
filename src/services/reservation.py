import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import NotFoundError, ReservationConflictError, ValidationError
from src.models.parking import ParkingSpace, Zone
from src.models.reservation import Reservation
from src.models.session import ParkingSession
from src.models.vehicle import Vehicle
from src.schemas.parking import ParkingSpaceResponse
from src.schemas.reservation import (
    AvailabilityResponse,
    CheckInResponse,
    ReservationCancelResponse,
    ReservationCreate,
    ReservationCreateResponse,
    ReservationListResponse,
    ReservationResponse,
    ReservationUpdate,
)
from src.services.session import generate_ticket_number
from src.utils.constants import ReservationStatus, SessionStatus, SpaceStatus


def generate_confirmation_number() -> str:
    return f"RSV-{uuid.uuid4().hex[:8].upper()}"


async def create_reservation(
    db: AsyncSession, user_id: int, data: ReservationCreate
) -> ReservationCreateResponse:
    start_time = data.start_time
    end_time = data.end_time
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=UTC)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=UTC)

    if start_time >= end_time:
        raise ValidationError("End time must be after start time")
    if start_time < datetime.now(UTC):
        raise ValidationError("Cannot create reservation in the past")

    if data.space_id:
        result = await db.execute(
            select(Reservation).where(
                Reservation.space_id == data.space_id,
                Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.CONFIRMED]),
                or_(
                    and_(
                        Reservation.start_time <= start_time,
                        Reservation.end_time > start_time,
                    ),
                    and_(
                        Reservation.start_time < end_time,
                        Reservation.end_time >= end_time,
                    ),
                    and_(
                        Reservation.start_time >= start_time,
                        Reservation.end_time <= end_time,
                    ),
                ),
            )
        )
        if result.scalar_one_or_none():
            raise ReservationConflictError("Space is already reserved for this time period")

        result = await db.execute(select(ParkingSpace).where(ParkingSpace.id == data.space_id))
        space = result.scalar_one_or_none()
        if not space:
            raise NotFoundError("Parking space not found")
        if space.status == SpaceStatus.AVAILABLE:
            space.status = SpaceStatus.RESERVED

    reservation = Reservation(
        user_id=user_id,
        vehicle_id=data.vehicle_id,
        space_id=data.space_id,
        zone_id=data.zone_id,
        start_time=start_time,
        end_time=end_time,
        status=ReservationStatus.CONFIRMED,
        confirmation_number=generate_confirmation_number(),
        reservation_fee=0,
        special_requests=data.special_requests,
    )
    db.add(reservation)
    await db.flush()

    result = await db.execute(
        select(Reservation)
        .where(Reservation.id == reservation.id)
        .options(
            selectinload(Reservation.vehicle).selectinload(Vehicle.vehicle_type),
            selectinload(Reservation.space).selectinload(ParkingSpace.zone).selectinload(Zone.level),
        )
    )
    reservation = result.scalar_one()

    return ReservationCreateResponse(
        reservation=ReservationResponse.model_validate(reservation),
        confirmation_number=reservation.confirmation_number,
    )


async def get_reservations(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    user_id: int | None = None,
    status: ReservationStatus | None = None,
) -> ReservationListResponse:
    query = select(Reservation).options(
        selectinload(Reservation.vehicle).selectinload(Vehicle.vehicle_type),
        selectinload(Reservation.space).selectinload(ParkingSpace.zone).selectinload(Zone.level),
    )
    count_query = select(func.count(Reservation.id))

    if user_id:
        query = query.where(Reservation.user_id == user_id)
        count_query = count_query.where(Reservation.user_id == user_id)
    if status:
        query = query.where(Reservation.status == status)
        count_query = count_query.where(Reservation.status == status)

    result = await db.execute(count_query)
    total = result.scalar() or 0

    offset = (page - 1) * limit
    result = await db.execute(query.offset(offset).limit(limit))
    reservations = result.scalars().all()

    return ReservationListResponse(
        reservations=[ReservationResponse.model_validate(r) for r in reservations],
        total=total,
        page=page,
        limit=limit,
    )


async def get_reservation_by_id(db: AsyncSession, reservation_id: int) -> ReservationResponse:
    result = await db.execute(
        select(Reservation)
        .where(Reservation.id == reservation_id)
        .options(
            selectinload(Reservation.vehicle).selectinload(Vehicle.vehicle_type),
            selectinload(Reservation.space).selectinload(ParkingSpace.zone).selectinload(Zone.level),
        )
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise NotFoundError("Reservation not found")
    return ReservationResponse.model_validate(reservation)


async def get_reservation_by_confirmation(
    db: AsyncSession, confirmation_number: str
) -> ReservationResponse:
    result = await db.execute(
        select(Reservation)
        .where(Reservation.confirmation_number == confirmation_number)
        .options(
            selectinload(Reservation.vehicle).selectinload(Vehicle.vehicle_type),
            selectinload(Reservation.space).selectinload(ParkingSpace.zone).selectinload(Zone.level),
        )
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise NotFoundError("Reservation not found")
    return ReservationResponse.model_validate(reservation)


async def update_reservation(
    db: AsyncSession, reservation_id: int, data: ReservationUpdate
) -> ReservationResponse:
    result = await db.execute(
        select(Reservation)
        .where(Reservation.id == reservation_id)
        .options(
            selectinload(Reservation.vehicle).selectinload(Vehicle.vehicle_type),
            selectinload(Reservation.space).selectinload(ParkingSpace.zone).selectinload(Zone.level),
        )
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise NotFoundError("Reservation not found")

    if reservation.status not in [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]:
        raise ValidationError("Cannot update reservation in current status")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(reservation, field, value)

    await db.flush()
    await db.refresh(reservation)
    return ReservationResponse.model_validate(reservation)


async def cancel_reservation(
    db: AsyncSession, reservation_id: int, reason: str | None = None
) -> ReservationCancelResponse:
    result = await db.execute(
        select(Reservation)
        .where(Reservation.id == reservation_id)
        .options(
            selectinload(Reservation.vehicle).selectinload(Vehicle.vehicle_type),
            selectinload(Reservation.space).selectinload(ParkingSpace.zone).selectinload(Zone.level),
        )
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise NotFoundError("Reservation not found")

    if reservation.status not in [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]:
        raise ValidationError("Cannot cancel reservation in current status")

    reservation.status = ReservationStatus.CANCELLED
    reservation.cancelled_at = datetime.now(UTC)
    reservation.cancellation_reason = reason
    if reservation.space_id:
        result = await db.execute(
            select(ParkingSpace).where(ParkingSpace.id == reservation.space_id)
        )
        space = result.scalar_one_or_none()
        if space and space.status == SpaceStatus.RESERVED:
            space.status = SpaceStatus.AVAILABLE

    await db.flush()
    await db.refresh(reservation)

    refund_amount = float(reservation.reservation_fee) if reservation.is_paid else None

    return ReservationCancelResponse(
        reservation=ReservationResponse.model_validate(reservation),
        refund_amount=refund_amount,
    )


async def check_in_reservation(db: AsyncSession, reservation_id: int) -> CheckInResponse:
    result = await db.execute(
        select(Reservation)
        .where(Reservation.id == reservation_id)
        .options(selectinload(Reservation.space).selectinload(ParkingSpace.zone).selectinload(Zone.level))
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise NotFoundError("Reservation not found")

    if reservation.status != ReservationStatus.CONFIRMED:
        raise ValidationError("Reservation is not confirmed")

    space_id = reservation.space_id
    if not space_id and reservation.zone_id:
        result = await db.execute(
            select(ParkingSpace)
            .where(
                ParkingSpace.zone_id == reservation.zone_id,
                ParkingSpace.status == SpaceStatus.AVAILABLE,
            )
            .options(selectinload(ParkingSpace.zone).selectinload(Zone.level))
            .limit(1)
        )
        space = result.scalar_one_or_none()
        if space:
            space_id = space.id

    if space_id:
        result = await db.execute(
            select(ParkingSpace)
            .where(ParkingSpace.id == space_id)
            .options(selectinload(ParkingSpace.zone).selectinload(Zone.level))
        )
        space = result.scalar_one()
        space.status = SpaceStatus.OCCUPIED

    session = ParkingSession(
        vehicle_id=reservation.vehicle_id,
        space_id=space_id,
        reservation_id=reservation_id,
        entry_time=datetime.now(UTC),
        ticket_number=generate_ticket_number(),
        status=SessionStatus.ACTIVE,
    )
    db.add(session)

    reservation.status = ReservationStatus.CHECKED_IN

    await db.flush()

    result = await db.execute(
        select(ParkingSpace)
        .where(ParkingSpace.id == space_id)
        .options(selectinload(ParkingSpace.zone).selectinload(Zone.level))
    )
    space = result.scalar_one_or_none()

    return CheckInResponse(
        session_id=session.id,
        space_assigned=ParkingSpaceResponse.model_validate(space) if space else None,
    )


async def check_availability(
    db: AsyncSession,
    start_time: datetime,
    end_time: datetime,
    zone_id: int | None = None,
) -> AvailabilityResponse:
    query = select(ParkingSpace).where(ParkingSpace.status == SpaceStatus.AVAILABLE).options(
        selectinload(ParkingSpace.zone).selectinload(Zone.level)
    )

    if zone_id:
        query = query.where(ParkingSpace.zone_id == zone_id)

    reserved_space_ids = select(Reservation.space_id).where(
        Reservation.space_id.isnot(None),
        Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.CONFIRMED]),
        or_(
            and_(Reservation.start_time <= start_time, Reservation.end_time > start_time),
            and_(Reservation.start_time < end_time, Reservation.end_time >= end_time),
            and_(Reservation.start_time >= start_time, Reservation.end_time <= end_time),
        ),
    )

    query = query.where(ParkingSpace.id.notin_(reserved_space_ids))

    result = await db.execute(query)
    spaces = result.scalars().all()

    return AvailabilityResponse(
        available_spaces=[ParkingSpaceResponse.model_validate(s) for s in spaces],
        total_available=len(spaces),
    )
