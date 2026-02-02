from datetime import datetime

from fastapi import APIRouter, Query

from src.core.dependencies import DB, ActiveUser, Pagination
from src.schemas.reservation import (
    AvailabilityResponse,
    CheckInResponse,
    ReservationCancelRequest,
    ReservationCancelResponse,
    ReservationCreate,
    ReservationCreateResponse,
    ReservationListResponse,
    ReservationResponse,
    ReservationUpdate,
)
from src.services import reservation as reservation_service
from src.utils.constants import ReservationStatus

router = APIRouter(prefix="/reservations", tags=["Reservations"])


@router.post("", response_model=ReservationCreateResponse)
async def create_reservation(db: DB, user: ActiveUser, data: ReservationCreate):
    return await reservation_service.create_reservation(db, user.id, data)


@router.get("", response_model=ReservationListResponse)
async def list_reservations(
    db: DB,
    user: ActiveUser,
    pagination: Pagination,
    status: ReservationStatus | None = Query(None),
):
    return await reservation_service.get_reservations(
        db, pagination.page, pagination.limit, user.id, status
    )


@router.get("/availability", response_model=AvailabilityResponse)
async def check_availability(
    db: DB,
    start_time: datetime,
    end_time: datetime,
    zone_id: int | None = Query(None),
):
    return await reservation_service.check_availability(db, start_time, end_time, zone_id)


@router.get("/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(db: DB, user: ActiveUser, reservation_id: int):
    return await reservation_service.get_reservation_by_id(db, reservation_id)


@router.get("/confirm/{confirmation_number}", response_model=ReservationResponse)
async def get_reservation_by_confirmation(db: DB, confirmation_number: str):
    return await reservation_service.get_reservation_by_confirmation(db, confirmation_number)


@router.put("/{reservation_id}", response_model=ReservationResponse)
async def update_reservation(
    db: DB, user: ActiveUser, reservation_id: int, data: ReservationUpdate
):
    return await reservation_service.update_reservation(db, reservation_id, data)


@router.post("/{reservation_id}/cancel", response_model=ReservationCancelResponse)
async def cancel_reservation(
    db: DB, user: ActiveUser, reservation_id: int, data: ReservationCancelRequest | None = None
):
    reason = data.reason if data else None
    return await reservation_service.cancel_reservation(db, reservation_id, reason)


@router.post("/{reservation_id}/check-in", response_model=CheckInResponse)
async def check_in_reservation(db: DB, user: ActiveUser, reservation_id: int):
    return await reservation_service.check_in_reservation(db, reservation_id)
