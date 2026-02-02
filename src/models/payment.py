from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel
from src.utils.constants import DiscountType, PaymentMethod, PaymentStatus, RateType


class Rate(BaseModel):
    __tablename__ = "rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    vehicle_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("vehicle_types.id"), nullable=True
    )
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id"), nullable=True)
    rate_type: Mapped[RateType] = mapped_column(default=RateType.HOURLY)
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    min_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grace_period_minutes: Mapped[int] = mapped_column(Integer, default=15)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    peak_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    peak_start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    peak_end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    vehicle_type: Mapped["VehicleType | None"] = relationship(back_populates="rates")  # noqa: F821
    zone: Mapped["Zone | None"] = relationship(back_populates="rates")  # noqa: F821


class Discount(BaseModel):
    __tablename__ = "discounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    discount_type: Mapped[DiscountType] = mapped_column(default=DiscountType.PERCENTAGE)
    value: Mapped[float] = mapped_column(Numeric(10, 2))
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_uses: Mapped[int] = mapped_column(Integer, default=0)
    max_uses_per_user: Mapped[int] = mapped_column(Integer, default=1)
    min_duration_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    partner_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    payments: Mapped[list["Payment"]] = relationship(back_populates="discount")


class Payment(BaseModel):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("parking_sessions.id"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    payment_method: Mapped[PaymentMethod] = mapped_column(default=PaymentMethod.CASH)
    status: Mapped[PaymentStatus] = mapped_column(default=PaymentStatus.PENDING)
    transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    discount_id: Mapped[int | None] = mapped_column(ForeignKey("discounts.id"), nullable=True)
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2))
    receipt_number: Mapped[str] = mapped_column(String(50), unique=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    session: Mapped["ParkingSession"] = relationship(back_populates="payment")  # noqa: F821
    discount: Mapped["Discount | None"] = relationship(back_populates="payments")
