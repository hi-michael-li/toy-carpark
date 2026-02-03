from fastapi import APIRouter, Query

from src.core.dependencies import AdminUser, DB, ActiveUser, Pagination
from src.core.exceptions import AuthorizationError
from src.schemas.common import MessageResponse
from src.schemas.vehicle import (
    VehicleCreate,
    VehicleListResponse,
    VehicleResponse,
    VehicleTypeCreate,
    VehicleTypeResponse,
    VehicleUpdate,
)
from src.services import vehicle as vehicle_service
from src.utils.constants import UserRole

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


@router.get("/types", response_model=list[VehicleTypeResponse])
async def list_vehicle_types(db: DB):
    return await vehicle_service.get_vehicle_types(db)


@router.post("/types", response_model=VehicleTypeResponse)
async def create_vehicle_type(db: DB, admin: AdminUser, data: VehicleTypeCreate):
    return await vehicle_service.create_vehicle_type(db, data)


@router.get("", response_model=VehicleListResponse)
async def list_vehicles(
    db: DB,
    user: ActiveUser,
    pagination: Pagination,
    user_id: int | None = Query(None),
):
    if user.role != UserRole.ADMIN:
        if user_id is not None and user_id != user.id:
            raise AuthorizationError("Not allowed to access other users' vehicles")
        user_id = user.id
    return await vehicle_service.get_vehicles(db, pagination.page, pagination.limit, user_id)


@router.post("", response_model=VehicleResponse)
async def create_vehicle(db: DB, user: ActiveUser, data: VehicleCreate):
    if data.user_id and user.role != UserRole.ADMIN and data.user_id != user.id:
        raise AuthorizationError("Not allowed to create vehicles for other users")
    if not data.user_id:
        data.user_id = user.id
    return await vehicle_service.create_vehicle(db, data)


@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(db: DB, user: ActiveUser, vehicle_id: int):
    vehicle = await vehicle_service.get_vehicle_by_id(db, vehicle_id)
    if user.role != UserRole.ADMIN and vehicle.user_id != user.id:
        raise AuthorizationError("Not allowed to access this vehicle")
    return vehicle


@router.get("/plate/{license_plate}", response_model=VehicleResponse | None)
async def get_vehicle_by_plate(db: DB, user: ActiveUser, license_plate: str):
    vehicle = await vehicle_service.get_vehicle_by_plate(db, license_plate)
    if vehicle and user.role != UserRole.ADMIN and vehicle.user_id != user.id:
        raise AuthorizationError("Not allowed to access this vehicle")
    return vehicle


@router.put("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(db: DB, user: ActiveUser, vehicle_id: int, data: VehicleUpdate):
    vehicle = await vehicle_service.get_vehicle_by_id(db, vehicle_id)
    if user.role != UserRole.ADMIN and vehicle.user_id != user.id:
        raise AuthorizationError("Not allowed to update this vehicle")
    return await vehicle_service.update_vehicle(db, vehicle_id, data)


@router.delete("/{vehicle_id}", response_model=MessageResponse)
async def delete_vehicle(db: DB, user: ActiveUser, vehicle_id: int):
    vehicle = await vehicle_service.get_vehicle_by_id(db, vehicle_id)
    if user.role != UserRole.ADMIN and vehicle.user_id != user.id:
        raise AuthorizationError("Not allowed to delete this vehicle")
    await vehicle_service.delete_vehicle(db, vehicle_id)
    return MessageResponse(message="Vehicle deleted successfully")
