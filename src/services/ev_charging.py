from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import NotFoundError, ValidationError
from src.models.ev_charging import ChargingSession, EVChargingStation
from src.models.parking import ParkingSpace, Zone
from src.schemas.ev_charging import (
    ChargingSessionListResponse,
    ChargingSessionResponse,
    ChargingSessionStart,
    ChargingSessionStopResponse,
    EVChargingStationCreate,
    EVChargingStationResponse,
    EVChargingStationUpdate,
)
from src.utils.constants import ChargingStatus, StationStatus


async def get_stations(
    db: AsyncSession,
    status: StationStatus | None = None,
    available_only: bool = False,
) -> list[EVChargingStationResponse]:
    query = select(EVChargingStation).options(
        selectinload(EVChargingStation.space)
        .selectinload(ParkingSpace.zone)
        .selectinload(Zone.level)
    )

    if status:
        query = query.where(EVChargingStation.status == status)
    if available_only:
        query = query.where(EVChargingStation.status == StationStatus.AVAILABLE)

    result = await db.execute(query)
    stations = result.scalars().all()
    return [EVChargingStationResponse.model_validate(s) for s in stations]


async def create_station(
    db: AsyncSession, data: EVChargingStationCreate
) -> EVChargingStationResponse:
    result = await db.execute(select(ParkingSpace).where(ParkingSpace.id == data.space_id))
    space = result.scalar_one_or_none()
    if not space:
        raise NotFoundError("Parking space not found")

    space.is_ev_charging = True

    station = EVChargingStation(**data.model_dump())
    db.add(station)
    await db.flush()

    result = await db.execute(
        select(EVChargingStation)
        .where(EVChargingStation.id == station.id)
        .options(selectinload(EVChargingStation.space).selectinload(ParkingSpace.zone).selectinload(Zone.level))
    )
    station = result.scalar_one()
    return EVChargingStationResponse.model_validate(station)


async def update_station(
    db: AsyncSession, station_id: int, data: EVChargingStationUpdate
) -> EVChargingStationResponse:
    result = await db.execute(
        select(EVChargingStation)
        .where(EVChargingStation.id == station_id)
        .options(selectinload(EVChargingStation.space).selectinload(ParkingSpace.zone).selectinload(Zone.level))
    )
    station = result.scalar_one_or_none()
    if not station:
        raise NotFoundError("Charging station not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(station, field, value)

    await db.flush()
    await db.refresh(station)
    return EVChargingStationResponse.model_validate(station)


async def start_charging(db: AsyncSession, data: ChargingSessionStart) -> ChargingSessionResponse:
    result = await db.execute(
        select(EVChargingStation).where(EVChargingStation.id == data.station_id)
    )
    station = result.scalar_one_or_none()
    if not station:
        raise NotFoundError("Charging station not found")

    if station.status != StationStatus.AVAILABLE:
        raise ValidationError("Charging station is not available")

    session = ChargingSession(
        station_id=data.station_id,
        vehicle_id=data.vehicle_id,
        parking_session_id=data.parking_session_id,
        start_time=datetime.now(UTC),
        status=ChargingStatus.CHARGING,
        max_power_requested=data.max_power_requested,
    )
    db.add(session)

    station.status = StationStatus.IN_USE

    await db.flush()
    await db.refresh(session)
    return ChargingSessionResponse.model_validate(session)


async def stop_charging(db: AsyncSession, session_id: int) -> ChargingSessionStopResponse:
    result = await db.execute(
        select(ChargingSession).where(ChargingSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError("Charging session not found")

    if session.status not in [ChargingStatus.STARTED, ChargingStatus.CHARGING]:
        raise ValidationError("Charging session is not active")

    end_time = datetime.now(UTC)
    session.end_time = end_time
    session.status = ChargingStatus.COMPLETED

    start_time = session.start_time
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=UTC)
    duration_minutes = int((end_time - start_time).total_seconds() / 60)
    hours = duration_minutes / 60

    result = await db.execute(
        select(EVChargingStation).where(EVChargingStation.id == session.station_id)
    )
    station = result.scalar_one()

    energy_kwh = hours * station.power_kw * 0.8
    session.energy_kwh = round(energy_kwh, 2)
    session.cost = round(energy_kwh * float(station.price_per_kwh), 2)

    station.status = StationStatus.AVAILABLE

    await db.flush()
    await db.refresh(session)

    return ChargingSessionStopResponse(
        session=ChargingSessionResponse.model_validate(session),
        energy_used=session.energy_kwh,
        cost=session.cost,
        duration_minutes=duration_minutes,
    )


async def get_charging_sessions(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    station_id: int | None = None,
    vehicle_id: int | None = None,
    status: ChargingStatus | None = None,
) -> ChargingSessionListResponse:
    query = select(ChargingSession)
    count_query = select(func.count(ChargingSession.id))

    if station_id:
        query = query.where(ChargingSession.station_id == station_id)
        count_query = count_query.where(ChargingSession.station_id == station_id)
    if vehicle_id:
        query = query.where(ChargingSession.vehicle_id == vehicle_id)
        count_query = count_query.where(ChargingSession.vehicle_id == vehicle_id)
    if status:
        query = query.where(ChargingSession.status == status)
        count_query = count_query.where(ChargingSession.status == status)

    result = await db.execute(count_query)
    total = result.scalar() or 0

    offset = (page - 1) * limit
    result = await db.execute(query.offset(offset).limit(limit))
    sessions = result.scalars().all()

    return ChargingSessionListResponse(
        sessions=[ChargingSessionResponse.model_validate(s) for s in sessions],
        total=total,
        page=page,
        limit=limit,
    )
