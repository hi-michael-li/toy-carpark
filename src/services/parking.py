from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import NotFoundError
from src.models.parking import Level, ParkingSpace, Zone
from src.schemas.parking import (
    LevelCreate,
    LevelResponse,
    LevelUpdate,
    ParkingSpaceCreate,
    ParkingSpaceListResponse,
    ParkingSpaceResponse,
    ParkingSpaceUpdate,
    ZoneAvailability,
    ZoneCreate,
    ZoneResponse,
    ZoneUpdate,
)
from src.utils.constants import SpaceStatus, SpaceType


async def get_levels(db: AsyncSession) -> list[LevelResponse]:
    result = await db.execute(select(Level).order_by(Level.floor_number))
    levels = result.scalars().all()
    return [LevelResponse.model_validate(level) for level in levels]


async def create_level(db: AsyncSession, data: LevelCreate) -> LevelResponse:
    level = Level(**data.model_dump())
    db.add(level)
    await db.flush()
    await db.refresh(level)
    return LevelResponse.model_validate(level)


async def update_level(db: AsyncSession, level_id: int, data: LevelUpdate) -> LevelResponse:
    result = await db.execute(select(Level).where(Level.id == level_id))
    level = result.scalar_one_or_none()
    if not level:
        raise NotFoundError("Level not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(level, field, value)

    await db.flush()
    await db.refresh(level)
    return LevelResponse.model_validate(level)


async def get_zones(db: AsyncSession, level_id: int | None = None) -> list[ZoneResponse]:
    query = select(Zone).options(selectinload(Zone.level))
    if level_id:
        query = query.where(Zone.level_id == level_id)
    result = await db.execute(query)
    zones = result.scalars().all()
    return [ZoneResponse.model_validate(zone) for zone in zones]


async def create_zone(db: AsyncSession, data: ZoneCreate) -> ZoneResponse:
    zone = Zone(**data.model_dump())
    db.add(zone)
    await db.flush()

    result = await db.execute(
        select(Zone).where(Zone.id == zone.id).options(selectinload(Zone.level))
    )
    zone = result.scalar_one()
    return ZoneResponse.model_validate(zone)


async def update_zone(db: AsyncSession, zone_id: int, data: ZoneUpdate) -> ZoneResponse:
    result = await db.execute(
        select(Zone).where(Zone.id == zone_id).options(selectinload(Zone.level))
    )
    zone = result.scalar_one_or_none()
    if not zone:
        raise NotFoundError("Zone not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(zone, field, value)

    await db.flush()
    await db.refresh(zone)
    return ZoneResponse.model_validate(zone)


async def get_zone_availability(db: AsyncSession, zone_id: int) -> ZoneAvailability:
    result = await db.execute(select(Zone).where(Zone.id == zone_id))
    zone = result.scalar_one_or_none()
    if not zone:
        raise NotFoundError("Zone not found")

    counts = {}
    for status in SpaceStatus:
        result = await db.execute(
            select(func.count(ParkingSpace.id)).where(
                ParkingSpace.zone_id == zone_id, ParkingSpace.status == status
            )
        )
        counts[status.value] = result.scalar() or 0

    total = sum(counts.values())
    available = counts.get(SpaceStatus.AVAILABLE.value, 0)
    occupancy_rate = ((total - available) / total * 100) if total > 0 else 0

    return ZoneAvailability(
        zone_id=zone_id,
        total=total,
        available=available,
        occupied=counts.get(SpaceStatus.OCCUPIED.value, 0),
        reserved=counts.get(SpaceStatus.RESERVED.value, 0),
        maintenance=counts.get(SpaceStatus.MAINTENANCE.value, 0),
        occupancy_rate=round(occupancy_rate, 2),
    )


async def get_spaces(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    zone_id: int | None = None,
    status: SpaceStatus | None = None,
    space_type: SpaceType | None = None,
) -> ParkingSpaceListResponse:
    query = select(ParkingSpace).options(selectinload(ParkingSpace.zone).selectinload(Zone.level))
    count_query = select(func.count(ParkingSpace.id))

    if zone_id:
        query = query.where(ParkingSpace.zone_id == zone_id)
        count_query = count_query.where(ParkingSpace.zone_id == zone_id)
    if status:
        query = query.where(ParkingSpace.status == status)
        count_query = count_query.where(ParkingSpace.status == status)
    if space_type:
        query = query.where(ParkingSpace.space_type == space_type)
        count_query = count_query.where(ParkingSpace.space_type == space_type)

    result = await db.execute(count_query)
    total = result.scalar() or 0

    offset = (page - 1) * limit
    result = await db.execute(query.offset(offset).limit(limit))
    spaces = result.scalars().all()

    return ParkingSpaceListResponse(
        spaces=[ParkingSpaceResponse.model_validate(s) for s in spaces],
        total=total,
        page=page,
        limit=limit,
    )


async def create_space(db: AsyncSession, data: ParkingSpaceCreate) -> ParkingSpaceResponse:
    space = ParkingSpace(**data.model_dump())
    db.add(space)
    await db.flush()

    result = await db.execute(
        select(ParkingSpace)
        .where(ParkingSpace.id == space.id)
        .options(selectinload(ParkingSpace.zone).selectinload(Zone.level))
    )
    space = result.scalar_one()
    return ParkingSpaceResponse.model_validate(space)


async def update_space(
    db: AsyncSession, space_id: int, data: ParkingSpaceUpdate
) -> ParkingSpaceResponse:
    result = await db.execute(
        select(ParkingSpace)
        .where(ParkingSpace.id == space_id)
        .options(selectinload(ParkingSpace.zone).selectinload(Zone.level))
    )
    space = result.scalar_one_or_none()
    if not space:
        raise NotFoundError("Parking space not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(space, field, value)

    await db.flush()
    await db.refresh(space)
    return ParkingSpaceResponse.model_validate(space)


async def get_available_spaces(
    db: AsyncSession,
    zone_id: int | None = None,
    is_ev: bool | None = None,
    limit: int = 50,
) -> list[ParkingSpaceResponse]:
    query = select(ParkingSpace).where(ParkingSpace.status == SpaceStatus.AVAILABLE)

    if zone_id:
        query = query.where(ParkingSpace.zone_id == zone_id)
    if is_ev:
        query = query.where(ParkingSpace.is_ev_charging == True)  # noqa: E712

    query = query.options(
        selectinload(ParkingSpace.zone).selectinload(Zone.level)
    ).limit(limit)
    result = await db.execute(query)
    spaces = result.scalars().all()

    return [ParkingSpaceResponse.model_validate(s) for s in spaces]
