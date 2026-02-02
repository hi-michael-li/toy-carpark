import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.models.vehicle import VehicleType
from src.utils.constants import UserRole


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
