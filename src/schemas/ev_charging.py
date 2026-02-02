from datetime import date, datetime

from src.schemas.common import BaseSchema, TimestampSchema
from src.schemas.parking import ParkingSpaceResponse
from src.utils.constants import ChargerType, ChargingStatus, StationStatus


class EVChargingStationBase(BaseSchema):
    charger_type: ChargerType = ChargerType.LEVEL2
    connector_type: str
    power_kw: float
    price_per_kwh: float
    manufacturer: str | None = None
    serial_number: str | None = None


class EVChargingStationCreate(EVChargingStationBase):
    space_id: int
    installed_at: date


class EVChargingStationUpdate(BaseSchema):
    status: StationStatus | None = None
    price_per_kwh: float | None = None
    last_maintenance: date | None = None


class EVChargingStationResponse(EVChargingStationBase, TimestampSchema):
    id: int
    space_id: int
    status: StationStatus
    installed_at: date
    last_maintenance: date | None = None
    space: ParkingSpaceResponse | None = None


class ChargingSessionStart(BaseSchema):
    station_id: int
    vehicle_id: int
    parking_session_id: int | None = None
    max_power_requested: float | None = None


class ChargingSessionResponse(TimestampSchema):
    id: int
    station_id: int
    vehicle_id: int
    parking_session_id: int | None = None
    start_time: datetime
    end_time: datetime | None = None
    energy_kwh: float
    cost: float
    status: ChargingStatus
    max_power_requested: float | None = None


class ChargingSessionStopResponse(BaseSchema):
    session: ChargingSessionResponse
    energy_used: float
    cost: float
    duration_minutes: int


class ChargingSessionListResponse(BaseSchema):
    sessions: list[ChargingSessionResponse]
    total: int
    page: int
    limit: int
