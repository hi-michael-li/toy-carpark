from datetime import datetime

from src.schemas.common import BaseSchema, TimestampSchema
from src.schemas.parking import ParkingSpaceResponse
from src.schemas.vehicle import VehicleResponse
from src.utils.constants import ReservationStatus


class ReservationBase(BaseSchema):
    start_time: datetime
    end_time: datetime
    special_requests: str | None = None


class ReservationCreate(ReservationBase):
    vehicle_id: int
    space_id: int | None = None
    zone_id: int | None = None


class ReservationUpdate(BaseSchema):
    start_time: datetime | None = None
    end_time: datetime | None = None
    space_id: int | None = None
    special_requests: str | None = None


class ReservationResponse(ReservationBase, TimestampSchema):
    id: int
    user_id: int
    vehicle_id: int
    space_id: int | None = None
    zone_id: int | None = None
    status: ReservationStatus
    confirmation_number: str
    reservation_fee: float
    is_paid: bool
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None
    vehicle: VehicleResponse | None = None
    space: ParkingSpaceResponse | None = None


class ReservationListResponse(BaseSchema):
    reservations: list[ReservationResponse]
    total: int
    page: int
    limit: int


class ReservationCreateResponse(BaseSchema):
    reservation: ReservationResponse
    confirmation_number: str


class ReservationCancelRequest(BaseSchema):
    reason: str | None = None


class ReservationCancelResponse(BaseSchema):
    reservation: ReservationResponse
    refund_amount: float | None = None


class CheckInResponse(BaseSchema):
    session_id: int
    space_assigned: ParkingSpaceResponse | None = None


class AvailabilityQuery(BaseSchema):
    start_time: datetime
    end_time: datetime
    zone_id: int | None = None
    vehicle_type_id: int | None = None


class AvailabilityResponse(BaseSchema):
    available_spaces: list[ParkingSpaceResponse]
    total_available: int
