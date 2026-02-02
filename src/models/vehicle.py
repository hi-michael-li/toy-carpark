from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel
from src.utils.constants import SizeCategory


class VehicleType(BaseModel):
    __tablename__ = "vehicle_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    size_category: Mapped[SizeCategory] = mapped_column(default=SizeCategory.MEDIUM)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="vehicle_type")
    rates: Mapped[list["Rate"]] = relationship(back_populates="vehicle_type")  # noqa: F821


class Vehicle(BaseModel):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    license_plate: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    vehicle_type_id: Mapped[int] = mapped_column(ForeignKey("vehicle_types.id"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    make: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_ev: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    vehicle_type: Mapped["VehicleType"] = relationship(back_populates="vehicles")
    owner: Mapped["User | None"] = relationship(back_populates="vehicles")  # noqa: F821
    sessions: Mapped[list["ParkingSession"]] = relationship(back_populates="vehicle")  # noqa: F821
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="vehicle")  # noqa: F821
    charging_sessions: Mapped[list["ChargingSession"]] = relationship(  # noqa: F821
        back_populates="vehicle"
    )
