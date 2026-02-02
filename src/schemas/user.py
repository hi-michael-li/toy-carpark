from datetime import date, datetime, time

from pydantic import EmailStr

from src.schemas.common import BaseSchema, TimestampSchema
from src.utils.constants import OperatorRole, UserRole


class UserBase(BaseSchema):
    email: EmailStr
    full_name: str
    phone: str | None = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseSchema):
    full_name: str | None = None
    phone: str | None = None


class UserResponse(UserBase, TimestampSchema):
    id: int
    role: UserRole
    is_active: bool
    is_verified: bool


class UserListResponse(BaseSchema):
    users: list[UserResponse]
    total: int
    page: int
    limit: int


class OperatorBase(BaseSchema):
    employee_id: str
    role: OperatorRole = OperatorRole.ATTENDANT
    permissions: dict | None = None
    shift_start: time | None = None
    shift_end: time | None = None


class OperatorCreate(OperatorBase):
    user_id: int
    hire_date: date


class OperatorUpdate(BaseSchema):
    role: OperatorRole | None = None
    permissions: dict | None = None
    shift_start: time | None = None
    shift_end: time | None = None


class OperatorResponse(OperatorBase, TimestampSchema):
    id: int
    user_id: int
    is_on_duty: bool
    hire_date: date


class ClockResponse(BaseSchema):
    operator: OperatorResponse
    action: str
    timestamp: datetime
