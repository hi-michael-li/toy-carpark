from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel
from src.utils.constants import ReservationStatus


class Reservation(BaseModel):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    space_id: Mapped[int | None] = mapped_column(ForeignKey("parking_spaces.id"), nullable=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id"), nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[ReservationStatus] = mapped_column(default=ReservationStatus.PENDING)
    confirmation_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    reservation_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    special_requests: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="reservations")  # noqa: F821
    vehicle: Mapped["Vehicle"] = relationship(back_populates="reservations")  # noqa: F821
    space: Mapped["ParkingSpace | None"] = relationship(back_populates="reservations")  # noqa: F821
    zone: Mapped["Zone | None"] = relationship()  # noqa: F821
    session: Mapped["ParkingSession | None"] = relationship(back_populates="reservation")  # noqa: F821
