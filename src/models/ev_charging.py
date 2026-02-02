from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel
from src.utils.constants import ChargerType, ChargingStatus, StationStatus


class EVChargingStation(BaseModel):
    __tablename__ = "ev_charging_stations"

    id: Mapped[int] = mapped_column(primary_key=True)
    space_id: Mapped[int] = mapped_column(ForeignKey("parking_spaces.id"), unique=True)
    charger_type: Mapped[ChargerType] = mapped_column(default=ChargerType.LEVEL2)
    connector_type: Mapped[str] = mapped_column(String(50))
    power_kw: Mapped[float] = mapped_column(Float)
    status: Mapped[StationStatus] = mapped_column(default=StationStatus.AVAILABLE)
    price_per_kwh: Mapped[float] = mapped_column(Numeric(10, 4))
    manufacturer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    installed_at: Mapped[date] = mapped_column(Date)
    last_maintenance: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships
    space: Mapped["ParkingSpace"] = relationship(back_populates="ev_station")  # noqa: F821
    charging_sessions: Mapped[list["ChargingSession"]] = relationship(back_populates="station")


class ChargingSession(BaseModel):
    __tablename__ = "charging_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("ev_charging_stations.id"))
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    parking_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("parking_sessions.id"), nullable=True
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    energy_kwh: Mapped[float] = mapped_column(Float, default=0)
    cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    status: Mapped[ChargingStatus] = mapped_column(default=ChargingStatus.STARTED)
    max_power_requested: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    station: Mapped["EVChargingStation"] = relationship(back_populates="charging_sessions")
    vehicle: Mapped["Vehicle"] = relationship(back_populates="charging_sessions")  # noqa: F821
