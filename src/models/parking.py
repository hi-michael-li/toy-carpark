from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel
from src.utils.constants import SpaceStatus, SpaceType


class Level(BaseModel):
    __tablename__ = "levels"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    floor_number: Mapped[int] = mapped_column(Integer)
    is_underground: Mapped[bool] = mapped_column(Boolean, default=False)
    max_height_m: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    zones: Mapped[list["Zone"]] = relationship(back_populates="level")


class Zone(BaseModel):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"))
    name: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_spaces: Mapped[int] = mapped_column(Integer, default=0)
    color_code: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Relationships
    level: Mapped["Level"] = relationship(back_populates="zones")
    spaces: Mapped[list["ParkingSpace"]] = relationship(back_populates="zone")
    rates: Mapped[list["Rate"]] = relationship(back_populates="zone")  # noqa: F821


class ParkingSpace(BaseModel):
    __tablename__ = "parking_spaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"))
    space_number: Mapped[str] = mapped_column(String(20), index=True)
    space_type: Mapped[SpaceType] = mapped_column(default=SpaceType.STANDARD)
    status: Mapped[SpaceStatus] = mapped_column(default=SpaceStatus.AVAILABLE)
    is_ev_charging: Mapped[bool] = mapped_column(Boolean, default=False)
    is_handicapped: Mapped[bool] = mapped_column(Boolean, default=False)
    floor: Mapped[int] = mapped_column(Integer)
    row: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Relationships
    zone: Mapped["Zone"] = relationship(back_populates="spaces")
    sessions: Mapped[list["ParkingSession"]] = relationship(back_populates="space")  # noqa: F821
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="space")  # noqa: F821
    ev_station: Mapped["EVChargingStation | None"] = relationship(back_populates="space")  # noqa: F821
