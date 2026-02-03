from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ev_charging import EVChargingStation
from src.models.parking import Level, ParkingSpace, Zone
from src.models.payment import Rate
from src.models.session import ParkingSession
from src.models.vehicle import Vehicle, VehicleType
from src.models.user import User
from src.utils.constants import (
    ChargerType,
    RateType,
    SessionStatus,
    SpaceStatus,
    StationStatus,
    UserRole,
)


@pytest.mark.asyncio
async def test_vehicle_entry_exit_flow(client: AsyncClient, db_session: AsyncSession):
    # Create an operator user for authentication
    from src.core.security import get_password_hash

    operator = User(
        email="operator@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Operator",
        role=UserRole.OPERATOR,
    )
    db_session.add(operator)
    await db_session.flush()

    # Login as operator
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": "operator@example.com", "password": "password123"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create vehicle type
    vehicle_type = VehicleType(name="Car", size_category="medium")
    db_session.add(vehicle_type)
    await db_session.commit()

    # Vehicle entry
    entry_response = await client.post(
        "/api/v1/sessions/entry",
        json={"license_plate": "ABC123", "entry_gate": "Gate A"},
        headers=headers,
    )
    assert entry_response.status_code == 200
    entry_data = entry_response.json()
    assert "ticket_number" in entry_data
    ticket_number = entry_data["ticket_number"]

    # Get session by ticket
    session_response = await client.get(
        f"/api/v1/sessions/ticket/{ticket_number}",
        headers=headers,
    )
    assert session_response.status_code == 200

    # Calculate fee
    session_id = entry_data["session"]["id"]
    fee_response = await client.get(
        f"/api/v1/sessions/{session_id}/calculate-fee",
        headers=headers,
    )
    assert fee_response.status_code == 200

    # Vehicle exit
    exit_response = await client.post(
        "/api/v1/sessions/exit",
        json={"ticket_number": ticket_number, "exit_gate": "Gate B"},
        headers=headers,
    )
    assert exit_response.status_code == 200
    exit_data = exit_response.json()
    assert "payment_due" in exit_data


@pytest.mark.asyncio
async def test_daily_cap_raised_for_ev_charging_space(
    client: AsyncClient, db_session: AsyncSession
):
    vehicle_type = VehicleType(name="EV", size_category="medium")
    db_session.add(vehicle_type)
    await db_session.flush()

    vehicle = Vehicle(license_plate="EV-CAP-1", vehicle_type_id=vehicle_type.id, is_ev=True)
    db_session.add(vehicle)
    await db_session.flush()

    level = Level(name="Cap Level", floor_number=1)
    db_session.add(level)
    await db_session.flush()

    zone = Zone(level_id=level.id, name="EV Cap Zone", total_spaces=5)
    db_session.add(zone)
    await db_session.flush()

    space = ParkingSpace(
        zone_id=zone.id,
        space_number="EV-CAP-01",
        floor=1,
        status=SpaceStatus.AVAILABLE,
        is_ev_charging=True,
    )
    db_session.add(space)
    await db_session.flush()

    station = EVChargingStation(
        space_id=space.id,
        charger_type=ChargerType.LEVEL2,
        connector_type="J1772",
        power_kw=10.0,
        price_per_kwh=0.50,
        status=StationStatus.AVAILABLE,
        installed_at=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(station)

    hourly_rate = Rate(
        name="Hourly",
        rate_type=RateType.HOURLY,
        amount=5.0,
        grace_period_minutes=15,
        effective_from=datetime.now(UTC) - timedelta(days=1),
        is_active=True,
    )
    daily_rate = Rate(
        name="Daily",
        rate_type=RateType.DAILY,
        amount=30.0,
        effective_from=datetime.now(UTC) - timedelta(days=1),
        is_active=True,
    )
    db_session.add_all([hourly_rate, daily_rate])

    entry_time = datetime.now(UTC) - timedelta(hours=20)
    parking_session = ParkingSession(
        vehicle_id=vehicle.id,
        space_id=space.id,
        entry_time=entry_time,
        ticket_number="TKT-EV-CAP-1",
        status=SessionStatus.ACTIVE,
    )
    db_session.add(parking_session)
    await db_session.commit()
    await db_session.refresh(parking_session)

    exit_time = entry_time + timedelta(hours=20)
    response = await client.get(
        f"/api/v1/sessions/{parking_session.id}/calculate-fee",
        params={"exit_time": exit_time.isoformat()},
    )
    assert response.status_code == 200
    data = response.json()

    hours = 20
    effective_hourly_rate = 5.0
    ev_rate = float(station.price_per_kwh) + 0.25
    ev_hourly = ev_rate * float(station.power_kw) * 0.8
    expected_daily_max = 30.0 + (ev_hourly - effective_hourly_rate) * hours
    expected_total = min(effective_hourly_rate * hours, expected_daily_max)
    assert data["total"] == round(expected_total, 2)
