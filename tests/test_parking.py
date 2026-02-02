import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import get_password_hash
from src.models.parking import Level, ParkingSpace, Zone
from src.models.user import User
from src.utils.constants import SpaceStatus, SpaceType, UserRole


async def create_admin_user(db_session: AsyncSession) -> User:
    """Helper to create an admin user."""
    admin = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpass123"),
        full_name="Admin User",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.commit()
    return admin


@pytest.fixture
async def admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    await create_admin_user(db_session)
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@example.com", "password": "adminpass123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_level(client: AsyncClient, admin_headers: dict):
    response = await client.post(
        "/api/v1/levels",
        json={
            "name": "Ground Floor",
            "floor_number": 0,
            "is_underground": False,
            "max_height_m": 2.5,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Ground Floor"
    assert data["floor_number"] == 0


@pytest.mark.asyncio
async def test_list_levels(client: AsyncClient, db_session: AsyncSession):
    levels = [
        Level(name="Basement 1", floor_number=-1, is_underground=True),
        Level(name="Ground", floor_number=0, is_underground=False),
        Level(name="Level 1", floor_number=1, is_underground=False),
    ]
    for level in levels:
        db_session.add(level)
    await db_session.commit()

    response = await client.get("/api/v1/levels")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_create_zone(client: AsyncClient, db_session: AsyncSession, admin_headers: dict):
    level = Level(name="Ground", floor_number=0)
    db_session.add(level)
    await db_session.commit()

    response = await client.post(
        "/api/v1/zones",
        json={
            "level_id": level.id,
            "name": "Zone A",
            "description": "Main parking area",
            "total_spaces": 50,
            "color_code": "#FF0000",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Zone A"
    assert data["total_spaces"] == 50


@pytest.mark.asyncio
async def test_list_zones(client: AsyncClient, db_session: AsyncSession):
    level = Level(name="Ground", floor_number=0)
    db_session.add(level)
    await db_session.flush()

    zones = [
        Zone(level_id=level.id, name="Zone A", total_spaces=30),
        Zone(level_id=level.id, name="Zone B", total_spaces=40),
    ]
    for zone in zones:
        db_session.add(zone)
    await db_session.commit()

    response = await client.get("/api/v1/zones")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_zone_availability(client: AsyncClient, db_session: AsyncSession):
    level = Level(name="Ground", floor_number=0)
    db_session.add(level)
    await db_session.flush()

    zone = Zone(level_id=level.id, name="Zone A", total_spaces=10)
    db_session.add(zone)
    await db_session.flush()

    # Create spaces with different statuses
    spaces = [
        ParkingSpace(zone_id=zone.id, space_number="A-001", floor=0, status=SpaceStatus.AVAILABLE),
        ParkingSpace(
            zone_id=zone.id, space_number="A-002", floor=0, status=SpaceStatus.AVAILABLE
        ),
        ParkingSpace(
            zone_id=zone.id, space_number="A-003", floor=0, status=SpaceStatus.OCCUPIED
        ),
        ParkingSpace(
            zone_id=zone.id, space_number="A-004", floor=0, status=SpaceStatus.RESERVED
        ),
        ParkingSpace(
            zone_id=zone.id, space_number="A-005", floor=0, status=SpaceStatus.MAINTENANCE
        ),
    ]
    for space in spaces:
        db_session.add(space)
    await db_session.commit()

    response = await client.get(f"/api/v1/zones/{zone.id}/availability")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert data["available"] == 2
    assert data["occupied"] == 1
    assert data["reserved"] == 1
    assert data["maintenance"] == 1


@pytest.mark.asyncio
async def test_create_parking_space(
    client: AsyncClient, db_session: AsyncSession, admin_headers: dict
):
    level = Level(name="Ground", floor_number=0)
    db_session.add(level)
    await db_session.flush()

    zone = Zone(level_id=level.id, name="Zone A", total_spaces=10)
    db_session.add(zone)
    await db_session.commit()

    response = await client.post(
        "/api/v1/spaces",
        json={
            "zone_id": zone.id,
            "space_number": "A-001",
            "space_type": "standard",
            "floor": 0,
            "is_ev_charging": False,
            "is_handicapped": False,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["space_number"] == "A-001"
    assert data["status"] == "available"


@pytest.mark.asyncio
async def test_list_spaces_with_filters(client: AsyncClient, db_session: AsyncSession):
    level = Level(name="Ground", floor_number=0)
    db_session.add(level)
    await db_session.flush()

    zone = Zone(level_id=level.id, name="Zone A", total_spaces=10)
    db_session.add(zone)
    await db_session.flush()

    spaces = [
        ParkingSpace(
            zone_id=zone.id,
            space_number="A-001",
            floor=0,
            space_type=SpaceType.STANDARD,
            status=SpaceStatus.AVAILABLE,
        ),
        ParkingSpace(
            zone_id=zone.id,
            space_number="A-002",
            floor=0,
            space_type=SpaceType.HANDICAPPED,
            status=SpaceStatus.AVAILABLE,
        ),
        ParkingSpace(
            zone_id=zone.id,
            space_number="A-003",
            floor=0,
            space_type=SpaceType.EV_CHARGING,
            status=SpaceStatus.OCCUPIED,
            is_ev_charging=True,
        ),
    ]
    for space in spaces:
        db_session.add(space)
    await db_session.commit()

    # Filter by status
    response = await client.get("/api/v1/spaces?status=available")
    assert response.status_code == 200
    assert response.json()["total"] == 2

    # Filter by space type
    response = await client.get("/api/v1/spaces?space_type=handicapped")
    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_get_available_spaces(client: AsyncClient, db_session: AsyncSession):
    level = Level(name="Ground", floor_number=0)
    db_session.add(level)
    await db_session.flush()

    zone = Zone(level_id=level.id, name="Zone A", total_spaces=10)
    db_session.add(zone)
    await db_session.flush()

    spaces = [
        ParkingSpace(zone_id=zone.id, space_number="A-001", floor=0, status=SpaceStatus.AVAILABLE),
        ParkingSpace(zone_id=zone.id, space_number="A-002", floor=0, status=SpaceStatus.AVAILABLE),
        ParkingSpace(zone_id=zone.id, space_number="A-003", floor=0, status=SpaceStatus.OCCUPIED),
    ]
    for space in spaces:
        db_session.add(space)
    await db_session.commit()

    response = await client.get("/api/v1/spaces/available")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_update_space_status(
    client: AsyncClient, db_session: AsyncSession, admin_headers: dict
):
    level = Level(name="Ground", floor_number=0)
    db_session.add(level)
    await db_session.flush()

    zone = Zone(level_id=level.id, name="Zone A", total_spaces=10)
    db_session.add(zone)
    await db_session.flush()

    space = ParkingSpace(
        zone_id=zone.id, space_number="A-001", floor=0, status=SpaceStatus.AVAILABLE
    )
    db_session.add(space)
    await db_session.commit()

    # Need operator permissions, admin should have them
    response = await client.patch(
        f"/api/v1/spaces/{space.id}/status",
        json={"status": "maintenance"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "maintenance"
