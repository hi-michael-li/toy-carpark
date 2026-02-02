from datetime import date, time

from sqlalchemy import JSON, Boolean, Date, ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel
from src.utils.constants import OperatorRole, UserRole


class User(BaseModel):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    role: Mapped[UserRole] = mapped_column(default=UserRole.CUSTOMER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="owner")  # noqa: F821
    memberships: Mapped[list["Membership"]] = relationship(back_populates="user")  # noqa: F821
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="user")  # noqa: F821
    operator: Mapped["Operator | None"] = relationship(back_populates="user")


class Operator(BaseModel):
    __tablename__ = "operators"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    employee_id: Mapped[str] = mapped_column(String(50), unique=True)
    role: Mapped[OperatorRole] = mapped_column(default=OperatorRole.ATTENDANT)
    permissions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    shift_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    shift_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    is_on_duty: Mapped[bool] = mapped_column(Boolean, default=False)
    hire_date: Mapped[date] = mapped_column(Date)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="operator")
