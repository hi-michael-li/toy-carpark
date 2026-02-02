from datetime import date

from src.schemas.common import BaseSchema, TimestampSchema
from src.utils.constants import MembershipStatus, PaymentMethod


class MembershipPlanBase(BaseSchema):
    name: str
    description: str | None = None
    duration_months: int
    price: float
    currency: str = "USD"
    vehicle_limit: int = 1
    included_hours: int | None = None
    discount_percentage: float = 0
    priority_reservation: bool = False
    ev_charging_included: bool = False


class MembershipPlanCreate(MembershipPlanBase):
    pass


class MembershipPlanUpdate(BaseSchema):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    is_active: bool | None = None


class MembershipPlanResponse(MembershipPlanBase, TimestampSchema):
    id: int
    is_active: bool


class MembershipBase(BaseSchema):
    auto_renew: bool = False


class MembershipCreate(MembershipBase):
    plan_id: int
    payment_method: PaymentMethod


class MembershipResponse(MembershipBase, TimestampSchema):
    id: int
    user_id: int
    plan_id: int
    start_date: date
    end_date: date
    status: MembershipStatus
    payment_method_id: str | None = None
    used_hours: float
    plan: MembershipPlanResponse | None = None


class MembershipListResponse(BaseSchema):
    memberships: list[MembershipResponse]
    total: int
    page: int
    limit: int


class MembershipSubscribeResponse(BaseSchema):
    membership: MembershipResponse
    payment_id: int


class MembershipUsageStats(BaseSchema):
    membership_id: int
    included_hours: int | None
    used_hours: float
    remaining_hours: float | None
    days_remaining: int
