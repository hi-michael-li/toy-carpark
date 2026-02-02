from datetime import datetime

from pydantic import field_validator

from src.schemas.common import BaseSchema, TimestampSchema
from src.schemas.parking import ParkingSpaceResponse
from src.schemas.vehicle import VehicleResponse
from src.utils.constants import SessionStatus


class SessionEntryRequest(BaseSchema):
    license_plate: str
    entry_gate: str | None = None
    lpr_image: str | None = None

    @field_validator("license_plate")
    @classmethod
    def validate_license_plate(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("License plate cannot be empty")
        if len(v) > 20:
            raise ValueError("License plate cannot exceed 20 characters")
        return v.upper()


class SessionExitRequest(BaseSchema):
    ticket_number: str | None = None
    license_plate: str | None = None
    exit_gate: str | None = None


class SessionBase(BaseSchema):
    entry_time: datetime
    exit_time: datetime | None = None
    ticket_number: str
    status: SessionStatus
    entry_gate: str | None = None
    exit_gate: str | None = None
    notes: str | None = None


class SessionResponse(SessionBase, TimestampSchema):
    id: int
    vehicle_id: int
    space_id: int | None = None
    reservation_id: int | None = None
    vehicle: VehicleResponse | None = None
    space: ParkingSpaceResponse | None = None


class SessionListResponse(BaseSchema):
    sessions: list[SessionResponse]
    total: int
    page: int
    limit: int


class SessionEntryResponse(BaseSchema):
    session: SessionResponse
    ticket_number: str
    space_assigned: ParkingSpaceResponse | None = None


class SessionExitResponse(BaseSchema):
    session: SessionResponse
    payment_due: float
    duration_minutes: int


class FeeCalculation(BaseSchema):
    session_id: int
    duration_minutes: int
    base_fee: float
    discounts: float
    tax: float
    total: float
    breakdown: list[dict]


class SpaceAssignRequest(BaseSchema):
    space_id: int
