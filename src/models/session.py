from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel
from src.utils.constants import SessionStatus


class ParkingSession(BaseModel):
    __tablename__ = "parking_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    space_id: Mapped[int | None] = mapped_column(ForeignKey("parking_spaces.id"), nullable=True)
    reservation_id: Mapped[int | None] = mapped_column(
        ForeignKey("reservations.id"), nullable=True
    )
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    exit_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ticket_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    status: Mapped[SessionStatus] = mapped_column(default=SessionStatus.ACTIVE)
    lpr_entry_image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lpr_exit_image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    entry_gate: Mapped[str | None] = mapped_column(String(50), nullable=True)
    exit_gate: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    vehicle: Mapped["Vehicle"] = relationship(back_populates="sessions")  # noqa: F821
    space: Mapped["ParkingSpace | None"] = relationship(back_populates="sessions")  # noqa: F821
    reservation: Mapped["Reservation | None"] = relationship(back_populates="session")  # noqa: F821
    payment: Mapped["Payment | None"] = relationship(back_populates="session")  # noqa: F821
