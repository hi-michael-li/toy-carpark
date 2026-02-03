from src.schemas.common import BaseSchema, TimestampSchema


class OrganizationCreate(BaseSchema):
    name: str
    notes: str | None = None
    billing_plan_id: int | None = None


class OrganizationUpdate(BaseSchema):
    name: str | None = None
    notes: str | None = None
    billing_plan_id: int | None = None


class OrganizationResponse(OrganizationCreate, TimestampSchema):
    id: int


class OrganizationPlanCreate(BaseSchema):
    name: str
    price: float
    currency: str = "USD"
    max_users: int | None = None
    max_spaces: int | None = None
    max_stations: int | None = None
    is_active: bool = True


class OrganizationPlanResponse(OrganizationPlanCreate, TimestampSchema):
    id: int
    organization_id: int | None = None


class OrganizationMemberCreate(BaseSchema):
    user_id: int
    role: str | None = None
    is_primary: bool = False


class OrganizationMemberResponse(OrganizationMemberCreate, TimestampSchema):
    id: int
    organization_id: int
