from src.schemas.common import BaseSchema, TimestampSchema
from src.utils.constants import SizeCategory


class VehicleTypeBase(BaseSchema):
    name: str
    size_category: SizeCategory = SizeCategory.MEDIUM
    description: str | None = None


class VehicleTypeCreate(VehicleTypeBase):
    pass


class VehicleTypeResponse(VehicleTypeBase, TimestampSchema):
    id: int


class VehicleBase(BaseSchema):
    license_plate: str
    vehicle_type_id: int
    make: str | None = None
    model: str | None = None
    color: str | None = None
    is_ev: bool = False


class VehicleCreate(VehicleBase):
    user_id: int | None = None


class VehicleUpdate(BaseSchema):
    make: str | None = None
    model: str | None = None
    color: str | None = None
    is_ev: bool | None = None


class VehicleResponse(VehicleBase, TimestampSchema):
    id: int
    user_id: int | None = None
    vehicle_type: VehicleTypeResponse | None = None


class VehicleListResponse(BaseSchema):
    vehicles: list[VehicleResponse]
    total: int
    page: int
    limit: int
