from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import get_password_hash
from src.models.ev_charging import EVChargingStation
from src.models.membership import Membership, MembershipPlan
from src.models.parking import Level, ParkingSpace, Zone
from src.models.payment import Payment
from src.models.session import ParkingSession
from src.models.user import User
from src.models.vehicle import Vehicle, VehicleType
from src.utils.constants import (
    ChargerType,
    MembershipStatus,
    PaymentMethod,
    PaymentStatus,
    SessionStatus,
    SpaceStatus,
    StationStatus,
    UserRole,
)


@pytest.fixture
async def admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    admin = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpass123"),
        full_name="Admin User",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.commit()

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@example.com", "password": "adminpass123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def setup_dashboard_data(db_session: AsyncSession):
    """Setup comprehensive data for dashboard testing."""
    # Vehicle type
    vehicle_type = VehicleType(name="Car", size_category="medium")
    db_session.add(vehicle_type)
    await db_session.flush()

    # Parking infrastructure
    level = Level(name="Ground", floor_number=0)
    db_session.add(level)
    await db_session.flush()

    zone = Zone(level_id=level.id, name="Zone A", total_spaces=20)
    db_session.add(zone)
    await db_session.flush()

    # Create spaces with mixed statuses
    spaces = []
    for i in range(20):
        status = SpaceStatus.AVAILABLE if i < 12 else SpaceStatus.OCCUPIED
        space = ParkingSpace(
            zone_id=zone.id,
            space_number=f"A-{i+1:03d}",
            floor=0,
            status=status,
            is_ev_charging=(i < 3),
        )
        db_session.add(space)
        spaces.append(space)
    await db_session.flush()

    # Create EV stations
    for i, space in enumerate(spaces[:3]):
        station = EVChargingStation(
            space_id=space.id,
            charger_type=ChargerType.LEVEL2,
            connector_type="J1772",
            power_kw=7.2,
            status=StationStatus.AVAILABLE if i < 2 else StationStatus.IN_USE,
            price_per_kwh=0.30,
            installed_at=datetime.now(UTC).date(),
        )
        db_session.add(station)
    await db_session.flush()

    # Create vehicles
    vehicles = []
    for i in range(5):
        vehicle = Vehicle(license_plate=f"DASH{i:03d}", vehicle_type_id=vehicle_type.id)
        db_session.add(vehicle)
        vehicles.append(vehicle)
    await db_session.flush()

    # Create sessions
    now = datetime.now(UTC)
    sessions = []
    for i, vehicle in enumerate(vehicles):
        status = SessionStatus.ACTIVE if i < 3 else SessionStatus.COMPLETED
        session = ParkingSession(
            vehicle_id=vehicle.id,
            space_id=spaces[12 + i].id if i < 3 else None,
            entry_time=now - timedelta(hours=i + 1),
            exit_time=now - timedelta(minutes=30) if status == SessionStatus.COMPLETED else None,
            ticket_number=f"TKT-DASH{i:03d}",
            status=status,
        )
        db_session.add(session)
        sessions.append(session)
    await db_session.flush()

    # Create payments for today
    for i, session in enumerate(sessions[3:]):  # Completed sessions
        payment = Payment(
            session_id=session.id,
            amount=10.0 + i * 5,
            payment_method=PaymentMethod.CARD,
            status=PaymentStatus.COMPLETED,
            total_amount=10.0 + i * 5,
            receipt_number=f"RCP-DASH{i:03d}",
            paid_at=now - timedelta(minutes=20),
        )
        db_session.add(payment)

    # Add a pending payment
    pending_payment = Payment(
        session_id=sessions[0].id,
        amount=15.0,
        payment_method=PaymentMethod.CASH,
        status=PaymentStatus.PENDING,
        total_amount=15.0,
        receipt_number="RCP-PENDING",
    )
    db_session.add(pending_payment)

    # Create membership plan and memberships
    plan = MembershipPlan(
        name="Basic",
        duration_months=1,
        price=50.0,
        is_active=True,
    )
    db_session.add(plan)
    await db_session.flush()

    # Create some active memberships
    for i in range(3):
        user = User(
            email=f"member{i}@example.com",
            hashed_password="hash",
            full_name=f"Member {i}",
        )
        db_session.add(user)
        await db_session.flush()

        membership = Membership(
            user_id=user.id,
            plan_id=plan.id,
            start_date=datetime.now(UTC).date(),
            end_date=(datetime.now(UTC) + timedelta(days=30)).date(),
            status=MembershipStatus.ACTIVE,
        )
        db_session.add(membership)

    await db_session.commit()

    return {
        "spaces": spaces,
        "sessions": sessions,
        "vehicles": vehicles,
    }


@pytest.mark.asyncio
async def test_dashboard_summary(
    client: AsyncClient, admin_headers: dict, setup_dashboard_data: dict
):
    response = await client.get("/api/v1/reports/dashboard", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()

    # Check all expected fields are present
    assert "current_occupancy" in data
    assert "total_spaces" in data
    assert "occupancy_rate" in data
    assert "today_revenue" in data
    assert "today_entries" in data
    assert "today_exits" in data
    assert "active_sessions" in data
    assert "pending_payments" in data
    assert "active_memberships" in data
    assert "ev_stations_available" in data
    assert "ev_stations_total" in data

    # Verify values
    assert data["total_spaces"] == 20
    assert data["current_occupancy"] == 8  # 8 occupied
    assert data["active_sessions"] == 3
    assert data["pending_payments"] >= 1
    assert data["active_memberships"] == 3
    assert data["ev_stations_total"] == 3
    assert data["ev_stations_available"] == 2


@pytest.mark.asyncio
async def test_dashboard_requires_admin(client: AsyncClient, auth_headers: dict):
    # Regular user should not have access
    response = await client.get("/api/v1/reports/dashboard", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_dashboard_with_no_data(client: AsyncClient, admin_headers: dict):
    # Should return zeros for empty database
    response = await client.get("/api/v1/reports/dashboard", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_spaces"] == 0
    assert data["current_occupancy"] == 0
    assert data["occupancy_rate"] == 0
