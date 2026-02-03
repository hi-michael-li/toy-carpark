import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import get_password_hash
from src.models.user import User
from src.models.vehicle import VehicleType
from src.utils.constants import SizeCategory, UserRole


async def create_admin_user(db_session: AsyncSession) -> User:
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
async def test_list_vehicle_types(client: AsyncClient, db_session: AsyncSession):
    # Create vehicle types
    types = [
        VehicleType(name="Motorcycle", size_category=SizeCategory.SMALL),
        VehicleType(name="Car", size_category=SizeCategory.MEDIUM),
        VehicleType(name="SUV", size_category=SizeCategory.LARGE),
    ]
    for t in types:
        db_session.add(t)
    await db_session.commit()

    response = await client.get("/api/v1/vehicles/types")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_create_vehicle_type(client: AsyncClient, admin_headers: dict):
    response = await client.post(
        "/api/v1/vehicles/types",
        json={"name": "Truck", "size_category": "extra_large", "description": "Large trucks"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Truck"
    assert data["size_category"] == "extra_large"


@pytest.mark.asyncio
async def test_create_vehicle(client: AsyncClient, db_session: AsyncSession, auth_headers: dict):
    # Create vehicle type first
    vehicle_type = VehicleType(name="Car", size_category=SizeCategory.MEDIUM)
    db_session.add(vehicle_type)
    await db_session.commit()

    response = await client.post(
        "/api/v1/vehicles",
        json={
            "license_plate": "ABC123",
            "vehicle_type_id": vehicle_type.id,
            "make": "Toyota",
            "model": "Camry",
            "color": "Blue",
            "is_ev": False,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["license_plate"] == "ABC123"
    assert data["make"] == "Toyota"


@pytest.mark.asyncio
async def test_get_vehicle_by_plate(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict
):
    # Create vehicle type and vehicle
    vehicle_type = VehicleType(name="Car", size_category=SizeCategory.MEDIUM)
    db_session.add(vehicle_type)
    await db_session.commit()

    await client.post(
        "/api/v1/vehicles",
        json={"license_plate": "XYZ789", "vehicle_type_id": vehicle_type.id},
        headers=auth_headers,
    )

    response = await client.get("/api/v1/vehicles/plate/XYZ789", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["license_plate"] == "XYZ789"


@pytest.mark.asyncio
async def test_update_vehicle(client: AsyncClient, db_session: AsyncSession, auth_headers: dict):
    vehicle_type = VehicleType(name="Car", size_category=SizeCategory.MEDIUM)
    db_session.add(vehicle_type)
    await db_session.commit()

    create_response = await client.post(
        "/api/v1/vehicles",
        json={"license_plate": "UPD123", "vehicle_type_id": vehicle_type.id, "color": "Red"},
        headers=auth_headers,
    )
    vehicle_id = create_response.json()["id"]

    response = await client.put(
        f"/api/v1/vehicles/{vehicle_id}",
        json={"color": "Green", "make": "Honda"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["color"] == "Green"
    assert data["make"] == "Honda"


@pytest.mark.asyncio
async def test_delete_vehicle(client: AsyncClient, db_session: AsyncSession, auth_headers: dict):
    vehicle_type = VehicleType(name="Car", size_category=SizeCategory.MEDIUM)
    db_session.add(vehicle_type)
    await db_session.commit()

    create_response = await client.post(
        "/api/v1/vehicles",
        json={"license_plate": "DEL123", "vehicle_type_id": vehicle_type.id},
        headers=auth_headers,
    )
    vehicle_id = create_response.json()["id"]

    response = await client.delete(f"/api/v1/vehicles/{vehicle_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Vehicle deleted successfully"


@pytest.mark.asyncio
async def test_list_vehicles(client: AsyncClient, db_session: AsyncSession, auth_headers: dict):
    vehicle_type = VehicleType(name="Car", size_category=SizeCategory.MEDIUM)
    db_session.add(vehicle_type)
    await db_session.commit()

    # Create multiple vehicles
    for plate in ["LIST001", "LIST002", "LIST003"]:
        await client.post(
            "/api/v1/vehicles",
            json={"license_plate": plate, "vehicle_type_id": vehicle_type.id},
            headers=auth_headers,
        )

    response = await client.get("/api/v1/vehicles", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3
    assert len(data["vehicles"]) >= 3


@pytest.mark.asyncio
async def test_duplicate_license_plate_rejected(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict
):
    vehicle_type = VehicleType(name="Car", size_category=SizeCategory.MEDIUM)
    db_session.add(vehicle_type)
    await db_session.commit()

    await client.post(
        "/api/v1/vehicles",
        json={"license_plate": "DUP123", "vehicle_type_id": vehicle_type.id},
        headers=auth_headers,
    )

    response = await client.post(
        "/api/v1/vehicles",
        json={"license_plate": "DUP123", "vehicle_type_id": vehicle_type.id},
        headers=auth_headers,
    )
    assert response.status_code == 409
