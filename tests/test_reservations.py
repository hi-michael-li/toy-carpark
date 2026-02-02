from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.parking import Level, ParkingSpace, Zone
from src.models.reservation import Reservation
from src.models.vehicle import Vehicle, VehicleType
from src.utils.constants import ReservationStatus, SpaceStatus


@pytest.fixture
async def setup_reservation_data(db_session: AsyncSession, test_user: dict):
    """Setup data needed for reservation tests."""
    vehicle_type = VehicleType(name="Car", size_category="medium")
    db_session.add(vehicle_type)
    await db_session.flush()

    level = Level(name="Ground", floor_number=0)
    db_session.add(level)
    await db_session.flush()

    zone = Zone(level_id=level.id, name="Zone A", total_spaces=10)
    db_session.add(zone)
    await db_session.flush()

    spaces = [
        ParkingSpace(
            zone_id=zone.id, space_number=f"A-00{i}", floor=0, status=SpaceStatus.AVAILABLE
        )
        for i in range(1, 6)
    ]
    for space in spaces:
        db_session.add(space)
    await db_session.flush()

    user_id = test_user["user"]["id"]
    vehicle = Vehicle(
        license_plate="RSV123",
        vehicle_type_id=vehicle_type.id,
        user_id=user_id,
    )
    db_session.add(vehicle)
    await db_session.commit()

    return {
        "vehicle_type": vehicle_type,
        "zone": zone,
        "spaces": spaces,
        "vehicle": vehicle,
        "user_id": user_id,
    }


@pytest.mark.asyncio
async def test_create_reservation(
    client: AsyncClient, auth_headers: dict, setup_reservation_data: dict
):
    vehicle = setup_reservation_data["vehicle"]
    zone = setup_reservation_data["zone"]

    start_time = datetime.now(UTC) + timedelta(hours=1)
    end_time = start_time + timedelta(hours=3)

    response = await client.post(
        "/api/v1/reservations",
        json={
            "vehicle_id": vehicle.id,
            "zone_id": zone.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "special_requests": "Near elevator please",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "confirmation_number" in data
    assert data["reservation"]["status"] == "confirmed"


@pytest.mark.asyncio
async def test_create_reservation_with_specific_space(
    client: AsyncClient, auth_headers: dict, setup_reservation_data: dict
):
    vehicle = setup_reservation_data["vehicle"]
    space = setup_reservation_data["spaces"][0]

    start_time = datetime.now(UTC) + timedelta(hours=2)
    end_time = start_time + timedelta(hours=2)

    response = await client.post(
        "/api/v1/reservations",
        json={
            "vehicle_id": vehicle.id,
            "space_id": space.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["reservation"]["space_id"] == space.id


@pytest.mark.asyncio
async def test_create_reservation_in_past_fails(
    client: AsyncClient, auth_headers: dict, setup_reservation_data: dict
):
    vehicle = setup_reservation_data["vehicle"]

    start_time = datetime.now(UTC) - timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)

    response = await client.post(
        "/api/v1/reservations",
        json={
            "vehicle_id": vehicle.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_reservation_end_before_start_fails(
    client: AsyncClient, auth_headers: dict, setup_reservation_data: dict
):
    vehicle = setup_reservation_data["vehicle"]

    start_time = datetime.now(UTC) + timedelta(hours=3)
    end_time = start_time - timedelta(hours=1)  # End before start

    response = await client.post(
        "/api/v1/reservations",
        json={
            "vehicle_id": vehicle.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_reservations(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, setup_reservation_data: dict
):
    vehicle = setup_reservation_data["vehicle"]
    user_id = setup_reservation_data["user_id"]

    # Create reservations directly
    for i in range(3):
        reservation = Reservation(
            user_id=user_id,
            vehicle_id=vehicle.id,
            start_time=datetime.now(UTC) + timedelta(days=i + 1),
            end_time=datetime.now(UTC) + timedelta(days=i + 1, hours=2),
            status=ReservationStatus.CONFIRMED,
            confirmation_number=f"RSV-LIST{i}",
        )
        db_session.add(reservation)
    await db_session.commit()

    response = await client.get("/api/v1/reservations", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_get_reservation_by_confirmation(
    client: AsyncClient, db_session: AsyncSession, setup_reservation_data: dict
):
    vehicle = setup_reservation_data["vehicle"]
    user_id = setup_reservation_data["user_id"]

    reservation = Reservation(
        user_id=user_id,
        vehicle_id=vehicle.id,
        start_time=datetime.now(UTC) + timedelta(hours=5),
        end_time=datetime.now(UTC) + timedelta(hours=7),
        status=ReservationStatus.CONFIRMED,
        confirmation_number="RSV-CONF123",
    )
    db_session.add(reservation)
    await db_session.commit()

    response = await client.get("/api/v1/reservations/confirm/RSV-CONF123")
    assert response.status_code == 200
    data = response.json()
    assert data["confirmation_number"] == "RSV-CONF123"


@pytest.mark.asyncio
async def test_cancel_reservation(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, setup_reservation_data: dict
):
    vehicle = setup_reservation_data["vehicle"]
    user_id = setup_reservation_data["user_id"]

    reservation = Reservation(
        user_id=user_id,
        vehicle_id=vehicle.id,
        start_time=datetime.now(UTC) + timedelta(hours=10),
        end_time=datetime.now(UTC) + timedelta(hours=12),
        status=ReservationStatus.CONFIRMED,
        confirmation_number="RSV-CANCEL1",
    )
    db_session.add(reservation)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/reservations/{reservation.id}/cancel",
        json={"reason": "Changed plans"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["reservation"]["status"] == "cancelled"


@pytest.mark.asyncio
async def test_check_availability(
    client: AsyncClient, db_session: AsyncSession, setup_reservation_data: dict
):
    zone = setup_reservation_data["zone"]

    start_time = datetime.now(UTC) + timedelta(days=5)
    end_time = start_time + timedelta(hours=2)

    response = await client.get(
        "/api/v1/reservations/availability",
        params={
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "zone_id": zone.id,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_available"] >= 1
    assert len(data["available_spaces"]) >= 1


@pytest.mark.asyncio
async def test_check_in_reservation(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, setup_reservation_data: dict
):
    vehicle = setup_reservation_data["vehicle"]
    user_id = setup_reservation_data["user_id"]
    zone = setup_reservation_data["zone"]

    reservation = Reservation(
        user_id=user_id,
        vehicle_id=vehicle.id,
        zone_id=zone.id,
        start_time=datetime.now(UTC) - timedelta(minutes=5),
        end_time=datetime.now(UTC) + timedelta(hours=2),
        status=ReservationStatus.CONFIRMED,
        confirmation_number="RSV-CHECKIN1",
    )
    db_session.add(reservation)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/reservations/{reservation.id}/check-in",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data


@pytest.mark.asyncio
async def test_update_reservation(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, setup_reservation_data: dict
):
    vehicle = setup_reservation_data["vehicle"]
    user_id = setup_reservation_data["user_id"]

    original_start = datetime.now(UTC) + timedelta(days=3)
    original_end = original_start + timedelta(hours=2)

    reservation = Reservation(
        user_id=user_id,
        vehicle_id=vehicle.id,
        start_time=original_start,
        end_time=original_end,
        status=ReservationStatus.CONFIRMED,
        confirmation_number="RSV-UPDATE1",
    )
    db_session.add(reservation)
    await db_session.commit()

    new_start = datetime.now(UTC) + timedelta(days=4)
    new_end = new_start + timedelta(hours=3)

    response = await client.put(
        f"/api/v1/reservations/{reservation.id}",
        json={
            "start_time": new_start.isoformat(),
            "end_time": new_end.isoformat(),
            "special_requests": "Window spot",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["special_requests"] == "Window spot"
