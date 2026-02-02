from src.schemas.common import BaseSchema, TimestampSchema
from src.utils.constants import SpaceStatus, SpaceType


class LevelBase(BaseSchema):
    name: str
    floor_number: int
    is_underground: bool = False
    max_height_m: float | None = None


class LevelCreate(LevelBase):
    pass


class LevelUpdate(BaseSchema):
    name: str | None = None
    max_height_m: float | None = None


class LevelResponse(LevelBase, TimestampSchema):
    id: int


class ZoneBase(BaseSchema):
    name: str
    description: str | None = None
    total_spaces: int = 0
    color_code: str | None = None


class ZoneCreate(ZoneBase):
    level_id: int


class ZoneUpdate(BaseSchema):
    name: str | None = None
    description: str | None = None
    color_code: str | None = None


class ZoneResponse(ZoneBase, TimestampSchema):
    id: int
    level_id: int
    level: LevelResponse | None = None


class ZoneAvailability(BaseSchema):
    zone_id: int
    total: int
    available: int
    occupied: int
    reserved: int
    maintenance: int
    occupancy_rate: float


class ParkingSpaceBase(BaseSchema):
    space_number: str
    space_type: SpaceType = SpaceType.STANDARD
    is_ev_charging: bool = False
    is_handicapped: bool = False
    floor: int
    row: str | None = None


class ParkingSpaceCreate(ParkingSpaceBase):
    zone_id: int


class ParkingSpaceUpdate(BaseSchema):
    status: SpaceStatus | None = None
    space_type: SpaceType | None = None


class ParkingSpaceResponse(ParkingSpaceBase, TimestampSchema):
    id: int
    zone_id: int
    status: SpaceStatus
    zone: ZoneResponse | None = None


class ParkingSpaceListResponse(BaseSchema):
    spaces: list[ParkingSpaceResponse]
    total: int
    page: int
    limit: int


class AvailableSpacesQuery(BaseSchema):
    vehicle_type_id: int | None = None
    zone_id: int | None = None
    is_ev: bool | None = None
