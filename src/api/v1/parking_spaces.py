from fastapi import APIRouter, Query

from src.core.dependencies import DB, ActiveUser, AdminUser, OperatorUser, Pagination
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
from src.services import parking as parking_service
from src.utils.constants import SpaceStatus, SpaceType

router = APIRouter(tags=["Parking"])


# Levels
@router.get("/levels", response_model=list[LevelResponse])
async def list_levels(db: DB):
    return await parking_service.get_levels(db)


@router.post("/levels", response_model=LevelResponse)
async def create_level(db: DB, admin: AdminUser, data: LevelCreate):
    return await parking_service.create_level(db, data)


@router.put("/levels/{level_id}", response_model=LevelResponse)
async def update_level(db: DB, admin: AdminUser, level_id: int, data: LevelUpdate):
    return await parking_service.update_level(db, level_id, data)


# Zones
@router.get("/zones", response_model=list[ZoneResponse])
async def list_zones(db: DB, level_id: int | None = Query(None)):
    return await parking_service.get_zones(db, level_id)


@router.post("/zones", response_model=ZoneResponse)
async def create_zone(db: DB, admin: AdminUser, data: ZoneCreate):
    return await parking_service.create_zone(db, data)


@router.put("/zones/{zone_id}", response_model=ZoneResponse)
async def update_zone(db: DB, admin: AdminUser, zone_id: int, data: ZoneUpdate):
    return await parking_service.update_zone(db, zone_id, data)


@router.get("/zones/{zone_id}/availability", response_model=ZoneAvailability)
async def get_zone_availability(db: DB, zone_id: int):
    return await parking_service.get_zone_availability(db, zone_id)


# Spaces
@router.get("/spaces", response_model=ParkingSpaceListResponse)
async def list_spaces(
    db: DB,
    pagination: Pagination,
    zone_id: int | None = Query(None),
    status: SpaceStatus | None = Query(None),
    space_type: SpaceType | None = Query(None),
):
    return await parking_service.get_spaces(
        db, pagination.page, pagination.limit, zone_id, status, space_type
    )


@router.post("/spaces", response_model=ParkingSpaceResponse)
async def create_space(db: DB, admin: AdminUser, data: ParkingSpaceCreate):
    return await parking_service.create_space(db, data)


@router.get("/spaces/available", response_model=list[ParkingSpaceResponse])
async def get_available_spaces(
    db: DB,
    zone_id: int | None = Query(None),
    is_ev: bool | None = Query(None),
    limit: int = Query(50, le=100),
):
    return await parking_service.get_available_spaces(db, zone_id, is_ev, limit)


@router.get("/spaces/{space_id}", response_model=ParkingSpaceResponse)
async def get_space(db: DB, user: ActiveUser, space_id: int):
    return await parking_service.get_space_by_id(db, space_id)


@router.patch("/spaces/{space_id}/status", response_model=ParkingSpaceResponse)
async def update_space_status(
    db: DB, operator: OperatorUser, space_id: int, data: ParkingSpaceUpdate
):
    return await parking_service.update_space(db, space_id, data)
