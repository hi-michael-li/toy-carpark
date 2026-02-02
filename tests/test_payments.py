from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import get_password_hash
from src.models.parking import Level, ParkingSpace, Zone
from src.models.payment import Payment, Rate
from src.models.session import ParkingSession
from src.models.user import User
from src.models.vehicle import Vehicle, VehicleType
from src.utils.constants import (
    PaymentMethod,
    PaymentStatus,
    RateType,
    SessionStatus,
    SpaceStatus,
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
async def setup_parking_data(db_session: AsyncSession):
    """Setup basic parking infrastructure."""
    vehicle_type = VehicleType(name="Car", size_category="medium")
    db_session.add(vehicle_type)

    level = Level(name="Ground", floor_number=0)
    db_session.add(level)
    await db_session.flush()

    zone = Zone(level_id=level.id, name="Zone A", total_spaces=10)
    db_session.add(zone)
    await db_session.flush()

    space = ParkingSpace(
        zone_id=zone.id, space_number="A-001", floor=0, status=SpaceStatus.OCCUPIED
    )
    db_session.add(space)

    vehicle = Vehicle(license_plate="PAY123", vehicle_type_id=vehicle_type.id)
    db_session.add(vehicle)
    await db_session.flush()

    # Create an active session
    session = ParkingSession(
        vehicle_id=vehicle.id,
        space_id=space.id,
        entry_time=datetime.now(UTC) - timedelta(hours=2),
        ticket_number="TKT-PAY001",
        status=SessionStatus.ACTIVE,
    )
    db_session.add(session)
    await db_session.commit()

    return {
        "vehicle_type": vehicle_type,
        "zone": zone,
        "space": space,
        "vehicle": vehicle,
        "session": session,
    }


@pytest.mark.asyncio
async def test_create_rate(client: AsyncClient, db_session: AsyncSession, admin_headers: dict):
    response = await client.post(
        "/api/v1/rates",
        json={
            "name": "Standard Hourly Rate",
            "rate_type": "hourly",
            "amount": 5.0,
            "currency": "USD",
            "grace_period_minutes": 15,
            "effective_from": datetime.now(UTC).isoformat(),
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Standard Hourly Rate"
    assert data["amount"] == 5.0


@pytest.mark.asyncio
async def test_list_rates(client: AsyncClient, db_session: AsyncSession):
    rates = [
        Rate(
            name="Hourly",
            rate_type=RateType.HOURLY,
            amount=5.0,
            effective_from=datetime.now(UTC),
            is_active=True,
        ),
        Rate(
            name="Daily",
            rate_type=RateType.DAILY,
            amount=30.0,
            effective_from=datetime.now(UTC),
            is_active=True,
        ),
    ]
    for rate in rates:
        db_session.add(rate)
    await db_session.commit()

    response = await client.get("/api/v1/rates")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_update_rate(client: AsyncClient, db_session: AsyncSession, admin_headers: dict):
    rate = Rate(
        name="Old Rate",
        rate_type=RateType.HOURLY,
        amount=5.0,
        effective_from=datetime.now(UTC),
        is_active=True,
    )
    db_session.add(rate)
    await db_session.commit()

    response = await client.put(
        f"/api/v1/rates/{rate.id}",
        json={"name": "Updated Rate", "amount": 6.0},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Rate"
    assert data["amount"] == 6.0


@pytest.mark.asyncio
async def test_deactivate_rate(client: AsyncClient, db_session: AsyncSession, admin_headers: dict):
    rate = Rate(
        name="To Deactivate",
        rate_type=RateType.HOURLY,
        amount=5.0,
        effective_from=datetime.now(UTC),
        is_active=True,
    )
    db_session.add(rate)
    await db_session.commit()

    response = await client.delete(f"/api/v1/rates/{rate.id}", headers=admin_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_process_payment(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, setup_parking_data: dict
):
    session = setup_parking_data["session"]

    response = await client.post(
        "/api/v1/payments",
        json={
            "session_id": session.id,
            "payment_method": "card",
            "amount": 10.0,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["payment_method"] == "card"
    assert "receipt_number" in data


@pytest.mark.asyncio
async def test_validate_exit_unpaid(
    client: AsyncClient, db_session: AsyncSession, setup_parking_data: dict
):
    session = setup_parking_data["session"]

    response = await client.post(
        "/api/v1/payments/validate-exit",
        json={"ticket_number": session.ticket_number},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_paid"] is False
    assert data["can_exit"] is False
    assert "amount_due" in data


@pytest.mark.asyncio
async def test_validate_exit_paid(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, setup_parking_data: dict
):
    session = setup_parking_data["session"]

    # Pay first
    await client.post(
        "/api/v1/payments",
        json={"session_id": session.id, "payment_method": "cash", "amount": 20.0},
        headers=auth_headers,
    )

    response = await client.post(
        "/api/v1/payments/validate-exit",
        json={"ticket_number": session.ticket_number},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_paid"] is True
    assert data["can_exit"] is True


@pytest.mark.asyncio
async def test_list_payments(
    client: AsyncClient, db_session: AsyncSession, admin_headers: dict, setup_parking_data: dict
):
    session = setup_parking_data["session"]

    # Create some payments
    for i in range(3):
        payment = Payment(
            session_id=session.id,
            amount=10.0,
            payment_method=PaymentMethod.CASH,
            status=PaymentStatus.COMPLETED,
            total_amount=10.0,
            receipt_number=f"RCP-TEST{i}",
            paid_at=datetime.now(UTC),
        )
        db_session.add(payment)
    await db_session.commit()

    response = await client.get("/api/v1/payments", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_payment_with_insufficient_amount(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, setup_parking_data: dict
):
    session = setup_parking_data["session"]

    # Create a rate so we have a fee to pay
    rate = Rate(
        name="Hourly",
        rate_type=RateType.HOURLY,
        amount=10.0,
        effective_from=datetime.now(UTC) - timedelta(days=1),
        is_active=True,
    )
    db_session.add(rate)
    await db_session.commit()

    response = await client.post(
        "/api/v1/payments",
        json={
            "session_id": session.id,
            "payment_method": "cash",
            "amount": 0.01,  # Way too little
        },
        headers=auth_headers,
    )
    assert response.status_code == 402  # Payment required


@pytest.mark.asyncio
async def test_duplicate_payment_rejected(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, setup_parking_data: dict
):
    session = setup_parking_data["session"]

    # First payment
    await client.post(
        "/api/v1/payments",
        json={"session_id": session.id, "payment_method": "cash", "amount": 20.0},
        headers=auth_headers,
    )

    # Second payment should fail
    response = await client.post(
        "/api/v1/payments",
        json={"session_id": session.id, "payment_method": "cash", "amount": 20.0},
        headers=auth_headers,
    )
    assert response.status_code == 402
