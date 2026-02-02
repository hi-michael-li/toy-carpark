from datetime import datetime

from fastapi import APIRouter, Query

from src.core.dependencies import DB, OperatorUser, Pagination
from src.schemas.session import (
    FeeCalculation,
    SessionEntryRequest,
    SessionEntryResponse,
    SessionExitRequest,
    SessionExitResponse,
    SessionListResponse,
    SessionResponse,
    SpaceAssignRequest,
)
from src.services import session as session_service

router = APIRouter(prefix="/sessions", tags=["Parking Sessions"])


@router.post("/entry", response_model=SessionEntryResponse)
async def vehicle_entry(db: DB, operator: OperatorUser, data: SessionEntryRequest):
    return await session_service.create_entry(db, data)


@router.post("/exit", response_model=SessionExitResponse)
async def vehicle_exit(db: DB, operator: OperatorUser, data: SessionExitRequest):
    return await session_service.process_exit(db, data)


@router.get("/active", response_model=SessionListResponse)
async def list_active_sessions(
    db: DB,
    operator: OperatorUser,
    pagination: Pagination,
    zone_id: int | None = Query(None),
):
    return await session_service.get_active_sessions(db, pagination.page, pagination.limit, zone_id)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(db: DB, operator: OperatorUser, session_id: int):
    return await session_service.get_session_by_id(db, session_id)


@router.get("/ticket/{ticket_number}", response_model=SessionResponse)
async def get_session_by_ticket(db: DB, ticket_number: str):
    return await session_service.get_session_by_ticket(db, ticket_number)


@router.get("/{session_id}/calculate-fee", response_model=FeeCalculation)
async def calculate_session_fee(
    db: DB,
    session_id: int,
    exit_time: datetime | None = Query(None),
):
    return await session_service.calculate_fee(db, session_id, exit_time)


@router.patch("/{session_id}/space", response_model=SessionResponse)
async def assign_space_to_session(
    db: DB, operator: OperatorUser, session_id: int, data: SpaceAssignRequest
):
    return await session_service.assign_space(db, session_id, data.space_id)


@router.post("/{session_id}/assign-space", response_model=SessionResponse)
async def assign_space_post(
    db: DB, operator: OperatorUser, session_id: int, data: SpaceAssignRequest
):
    """Alternative POST endpoint for assigning space to a session."""
    return await session_service.assign_space(db, session_id, data.space_id)


@router.post("/{session_id}/complete", response_model=SessionResponse)
async def complete_session(db: DB, operator: OperatorUser, session_id: int):
    return await session_service.complete_session(db, session_id)
