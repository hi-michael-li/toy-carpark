from fastapi import APIRouter, Query

from src.core.dependencies import DB, ActiveUser, AdminUser, Pagination
from src.schemas.payment import (
    PaymentCreate,
    PaymentListResponse,
    PaymentResponse,
    ValidateExitRequest,
    ValidateExitResponse,
)
from src.services import payment as payment_service
from src.utils.constants import PaymentStatus

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("", response_model=PaymentResponse)
async def process_payment(db: DB, user: ActiveUser, data: PaymentCreate):
    return await payment_service.process_payment(db, data, user.id)


@router.get("", response_model=PaymentListResponse)
async def list_payments(
    db: DB,
    admin: AdminUser,
    pagination: Pagination,
    status: PaymentStatus | None = Query(None),
):
    return await payment_service.get_payments(db, pagination.page, pagination.limit, status)


@router.post("/validate-exit", response_model=ValidateExitResponse)
async def validate_exit(db: DB, data: ValidateExitRequest):
    return await payment_service.validate_exit(db, data.ticket_number)
