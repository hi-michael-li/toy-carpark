from fastapi import APIRouter, Query

from src.core.dependencies import DB, AdminUser
from src.schemas.common import MessageResponse
from src.schemas.payment import RateCreate, RateResponse, RateUpdate
from src.services import payment as payment_service

router = APIRouter(prefix="/rates", tags=["Rates"])


@router.get("", response_model=list[RateResponse])
async def list_rates(
    db: DB,
    vehicle_type_id: int | None = Query(None),
    zone_id: int | None = Query(None),
    is_active: bool = Query(True),
):
    return await payment_service.get_rates(db, vehicle_type_id, zone_id, is_active)


@router.post("", response_model=RateResponse)
async def create_rate(db: DB, admin: AdminUser, data: RateCreate):
    return await payment_service.create_rate(db, data)


@router.put("/{rate_id}", response_model=RateResponse)
async def update_rate(db: DB, admin: AdminUser, rate_id: int, data: RateUpdate):
    return await payment_service.update_rate(db, rate_id, data)


@router.delete("/{rate_id}", response_model=MessageResponse)
async def deactivate_rate(db: DB, admin: AdminUser, rate_id: int):
    await payment_service.update_rate(db, rate_id, RateUpdate(is_active=False))
    return MessageResponse(message="Rate deactivated successfully")
