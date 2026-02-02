from fastapi import APIRouter, Query

from src.core.dependencies import DB, AdminUser
from src.schemas.common import MessageResponse
from src.schemas.payment import (
    DiscountCreate,
    DiscountResponse,
    DiscountUpdate,
    DiscountValidation,
    DiscountValidationResponse,
)
from src.services import payment as payment_service

router = APIRouter(prefix="/discounts", tags=["Discounts"])


@router.get("", response_model=list[DiscountResponse])
async def list_discounts(
    db: DB,
    admin: AdminUser,
    is_active: bool = Query(True),
    partner_name: str | None = Query(None),
):
    return await payment_service.get_discounts(db, is_active, partner_name)


@router.post("", response_model=DiscountResponse)
async def create_discount(db: DB, admin: AdminUser, data: DiscountCreate):
    return await payment_service.create_discount(db, data)


@router.put("/{discount_id}", response_model=DiscountResponse)
async def update_discount(db: DB, admin: AdminUser, discount_id: int, data: DiscountUpdate):
    return await payment_service.update_discount(db, discount_id, data)


@router.delete("/{discount_id}", response_model=MessageResponse)
async def deactivate_discount(db: DB, admin: AdminUser, discount_id: int):
    await payment_service.update_discount(db, discount_id, DiscountUpdate(is_active=False))
    return MessageResponse(message="Discount deactivated successfully")


@router.post("/validate", response_model=DiscountValidationResponse)
async def validate_discount(db: DB, data: DiscountValidation):
    return await payment_service.validate_discount(db, data.code, data.session_id)
