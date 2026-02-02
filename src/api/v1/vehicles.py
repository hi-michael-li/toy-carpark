from fastapi import APIRouter, Query

from src.core.dependencies import DB, ActiveUser, Pagination
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

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


@router.get("/types", response_model=list[VehicleTypeResponse])
async def list_vehicle_types(db: DB):
    return await vehicle_service.get_vehicle_types(db)


@router.post("/types", response_model=VehicleTypeResponse)
async def create_vehicle_type(db: DB, user: ActiveUser, data: VehicleTypeCreate):
    return await vehicle_service.create_vehicle_type(db, data)


@router.get("", response_model=VehicleListResponse)
async def list_vehicles(
    db: DB,
    user: ActiveUser,
    pagination: Pagination,
    user_id: int | None = Query(None),
):
    return await vehicle_service.get_vehicles(db, pagination.page, pagination.limit, user_id)


@router.post("", response_model=VehicleResponse)
async def create_vehicle(db: DB, user: ActiveUser, data: VehicleCreate):
    if not data.user_id:
        data.user_id = user.id
    return await vehicle_service.create_vehicle(db, data)


@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(db: DB, user: ActiveUser, vehicle_id: int):
    return await vehicle_service.get_vehicle_by_id(db, vehicle_id)


@router.get("/plate/{license_plate}", response_model=VehicleResponse | None)
async def get_vehicle_by_plate(db: DB, user: ActiveUser, license_plate: str):
    return await vehicle_service.get_vehicle_by_plate(db, license_plate)


@router.put("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(db: DB, user: ActiveUser, vehicle_id: int, data: VehicleUpdate):
    return await vehicle_service.update_vehicle(db, vehicle_id, data)


@router.delete("/{vehicle_id}", response_model=MessageResponse)
async def delete_vehicle(db: DB, user: ActiveUser, vehicle_id: int):
    await vehicle_service.delete_vehicle(db, vehicle_id)
    return MessageResponse(message="Vehicle deleted successfully")
