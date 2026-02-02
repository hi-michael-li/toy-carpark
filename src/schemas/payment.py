from datetime import datetime, time

from src.schemas.common import BaseSchema, TimestampSchema
from src.utils.constants import DiscountType, PaymentMethod, PaymentStatus, RateType


class RateBase(BaseSchema):
    name: str
    rate_type: RateType = RateType.HOURLY
    amount: float
    currency: str = "USD"
    min_duration_minutes: int | None = None
    max_duration_minutes: int | None = None
    grace_period_minutes: int = 15
    peak_multiplier: float = 1.0
    peak_start_time: time | None = None
    peak_end_time: time | None = None


class RateCreate(RateBase):
    vehicle_type_id: int | None = None
    zone_id: int | None = None
    effective_from: datetime
    effective_to: datetime | None = None


class RateUpdate(BaseSchema):
    name: str | None = None
    amount: float | None = None
    is_active: bool | None = None
    peak_multiplier: float | None = None


class RateResponse(RateBase, TimestampSchema):
    id: int
    vehicle_type_id: int | None = None
    zone_id: int | None = None
    effective_from: datetime
    effective_to: datetime | None = None
    is_active: bool


class RateCalculation(BaseSchema):
    rate: RateResponse
    amount: float
    duration_hours: float


class DiscountBase(BaseSchema):
    code: str
    name: str
    discount_type: DiscountType = DiscountType.PERCENTAGE
    value: float
    valid_from: datetime
    valid_to: datetime
    max_uses: int | None = None
    max_uses_per_user: int = 1
    min_duration_hours: int | None = None
    partner_name: str | None = None


class DiscountCreate(DiscountBase):
    pass


class DiscountUpdate(BaseSchema):
    name: str | None = None
    value: float | None = None
    valid_to: datetime | None = None
    max_uses: int | None = None
    is_active: bool | None = None


class DiscountResponse(DiscountBase, TimestampSchema):
    id: int
    current_uses: int
    is_active: bool


class DiscountValidation(BaseSchema):
    code: str
    session_id: int | None = None


class DiscountValidationResponse(BaseSchema):
    is_valid: bool
    discount: DiscountResponse | None = None
    discount_amount: float | None = None
    message: str | None = None


class PaymentCreate(BaseSchema):
    session_id: int
    payment_method: PaymentMethod
    discount_code: str | None = None
    amount: float


class PaymentResponse(TimestampSchema):
    id: int
    session_id: int
    user_id: int | None = None
    amount: float
    currency: str
    payment_method: PaymentMethod
    status: PaymentStatus
    transaction_id: str | None = None
    discount_id: int | None = None
    discount_amount: float
    tax_amount: float
    total_amount: float
    receipt_number: str
    paid_at: datetime | None = None


class PaymentListResponse(BaseSchema):
    payments: list[PaymentResponse]
    total: int
    total_amount: float
    page: int
    limit: int


class ValidateExitRequest(BaseSchema):
    ticket_number: str


class ValidateExitResponse(BaseSchema):
    is_paid: bool
    can_exit: bool
    time_remaining_minutes: int | None = None
    amount_due: float | None = None
