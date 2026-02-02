from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel
from src.utils.constants import MembershipStatus


class MembershipPlan(BaseModel):
    __tablename__ = "membership_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_months: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    vehicle_limit: Mapped[int] = mapped_column(Integer, default=1)
    included_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_percentage: Mapped[float] = mapped_column(Float, default=0)
    priority_reservation: Mapped[bool] = mapped_column(Boolean, default=False)
    ev_charging_included: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    memberships: Mapped[list["Membership"]] = relationship(back_populates="plan")


class Membership(BaseModel):
    __tablename__ = "memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    plan_id: Mapped[int] = mapped_column(ForeignKey("membership_plans.id"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[MembershipStatus] = mapped_column(default=MembershipStatus.ACTIVE)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)
    payment_method_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    used_hours: Mapped[float] = mapped_column(Float, default=0)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="memberships")  # noqa: F821
    plan: Mapped["MembershipPlan"] = relationship(back_populates="memberships")
