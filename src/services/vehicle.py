from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ConflictError, NotFoundError
from src.models.vehicle import Vehicle, VehicleType
from src.schemas.vehicle import (
    VehicleCreate,
    VehicleListResponse,
    VehicleResponse,
    VehicleTypeCreate,
    VehicleTypeResponse,
    VehicleUpdate,
)


async def get_vehicle_types(db: AsyncSession) -> list[VehicleTypeResponse]:
    result = await db.execute(select(VehicleType))
    types = result.scalars().all()
    return [VehicleTypeResponse.model_validate(t) for t in types]


async def create_vehicle_type(db: AsyncSession, data: VehicleTypeCreate) -> VehicleTypeResponse:
    vehicle_type = VehicleType(**data.model_dump())
    db.add(vehicle_type)
    await db.flush()
    await db.refresh(vehicle_type)
    return VehicleTypeResponse.model_validate(vehicle_type)


async def get_vehicle_by_id(db: AsyncSession, vehicle_id: int) -> VehicleResponse:
    result = await db.execute(
        select(Vehicle).where(Vehicle.id == vehicle_id).options(selectinload(Vehicle.vehicle_type))
    )
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise NotFoundError("Vehicle not found")
    return VehicleResponse.model_validate(vehicle)


async def get_vehicle_by_plate(db: AsyncSession, license_plate: str) -> VehicleResponse | None:
    result = await db.execute(
        select(Vehicle)
        .where(Vehicle.license_plate == license_plate.upper())
        .options(selectinload(Vehicle.vehicle_type))
    )
    vehicle = result.scalar_one_or_none()
    if vehicle:
        return VehicleResponse.model_validate(vehicle)
    return None


async def get_vehicles(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    user_id: int | None = None,
) -> VehicleListResponse:
    query = select(Vehicle).options(selectinload(Vehicle.vehicle_type))
    count_query = select(func.count(Vehicle.id))

    if user_id:
        query = query.where(Vehicle.user_id == user_id)
        count_query = count_query.where(Vehicle.user_id == user_id)

    result = await db.execute(count_query)
    total = result.scalar() or 0

    offset = (page - 1) * limit
    result = await db.execute(query.offset(offset).limit(limit))
    vehicles = result.scalars().all()

    return VehicleListResponse(
        vehicles=[VehicleResponse.model_validate(v) for v in vehicles],
        total=total,
        page=page,
        limit=limit,
    )


async def create_vehicle(db: AsyncSession, data: VehicleCreate) -> VehicleResponse:
    result = await db.execute(
        select(Vehicle).where(Vehicle.license_plate == data.license_plate.upper())
    )
    if result.scalar_one_or_none():
        raise ConflictError("Vehicle with this license plate already exists")

    vehicle = Vehicle(**data.model_dump())
    vehicle.license_plate = vehicle.license_plate.upper()
    db.add(vehicle)
    await db.flush()

    result = await db.execute(
        select(Vehicle).where(Vehicle.id == vehicle.id).options(selectinload(Vehicle.vehicle_type))
    )
    vehicle = result.scalar_one()
    return VehicleResponse.model_validate(vehicle)


async def update_vehicle(db: AsyncSession, vehicle_id: int, data: VehicleUpdate) -> VehicleResponse:
    result = await db.execute(
        select(Vehicle).where(Vehicle.id == vehicle_id).options(selectinload(Vehicle.vehicle_type))
    )
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise NotFoundError("Vehicle not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vehicle, field, value)

    await db.flush()
    await db.refresh(vehicle)
    return VehicleResponse.model_validate(vehicle)


async def delete_vehicle(db: AsyncSession, vehicle_id: int) -> None:
    result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise NotFoundError("Vehicle not found")

    await db.delete(vehicle)
