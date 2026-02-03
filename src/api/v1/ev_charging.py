from fastapi import APIRouter, Query

from src.core.dependencies import DB, ActiveUser, AdminUser, Pagination
from src.schemas.ev_charging import (
    ChargingSessionListResponse,
    ChargingSessionResponse,
    ChargingSessionStart,
    ChargingSessionStopResponse,
    EVChargingStationCreate,
    EVChargingStationResponse,
    EVChargingStationUpdate,
)
from src.services import ev_charging as ev_service
from src.utils.constants import ChargingStatus, StationStatus

router = APIRouter(prefix="/ev", tags=["EV Charging"])


# Stations
@router.get("/stations", response_model=list[EVChargingStationResponse])
async def list_stations(
    db: DB,
    status: StationStatus | None = Query(None),
    available_only: bool = Query(False),
):
    return await ev_service.get_stations(db, status, available_only)


@router.post("/stations", response_model=EVChargingStationResponse)
async def create_station(db: DB, admin: AdminUser, data: EVChargingStationCreate):
    return await ev_service.create_station(db, data)


@router.put("/stations/{station_id}", response_model=EVChargingStationResponse)
async def update_station(
    db: DB, admin: AdminUser, station_id: int, data: EVChargingStationUpdate
):
    return await ev_service.update_station(db, station_id, data)


# Charging Sessions
@router.post("/charging/start", response_model=ChargingSessionResponse)
async def start_charging(db: DB, user: ActiveUser, data: ChargingSessionStart):
    return await ev_service.start_charging(db, data)


@router.post("/charging/{session_id}/stop", response_model=ChargingSessionStopResponse)
async def stop_charging(
    db: DB,
    user: ActiveUser,
    session_id: int,
    p: str | None = Query(None),
):
    return await ev_service.stop_charging(db, session_id, p)


@router.get("/charging", response_model=ChargingSessionListResponse)
async def list_charging_sessions(
    db: DB,
    user: ActiveUser,
    pagination: Pagination,
    station_id: int | None = Query(None),
    vehicle_id: int | None = Query(None),
    status: ChargingStatus | None = Query(None),
):
    return await ev_service.get_charging_sessions(
        db, pagination.page, pagination.limit, station_id, vehicle_id, status
    )
