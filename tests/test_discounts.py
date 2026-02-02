from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import get_password_hash
from src.models.payment import Discount
from src.models.user import User
from src.utils.constants import DiscountType, UserRole


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


@pytest.mark.asyncio
async def test_create_discount(client: AsyncClient, admin_headers: dict):
    response = await client.post(
        "/api/v1/discounts",
        json={
            "code": "SAVE20",
            "name": "20% Off",
            "discount_type": "percentage",
            "value": 20.0,
            "valid_from": datetime.now(UTC).isoformat(),
            "valid_to": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            "max_uses": 100,
            "partner_name": "Local Mall",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "SAVE20"
    assert data["value"] == 20.0
    assert data["discount_type"] == "percentage"


@pytest.mark.asyncio
async def test_list_discounts(client: AsyncClient, db_session: AsyncSession, admin_headers: dict):
    discounts = [
        Discount(
            code="DISC1",
            name="Discount 1",
            discount_type=DiscountType.PERCENTAGE,
            value=10.0,
            valid_from=datetime.now(UTC),
            valid_to=datetime.now(UTC) + timedelta(days=30),
            is_active=True,
        ),
        Discount(
            code="DISC2",
            name="Discount 2",
            discount_type=DiscountType.FIXED_AMOUNT,
            value=5.0,
            valid_from=datetime.now(UTC),
            valid_to=datetime.now(UTC) + timedelta(days=30),
            is_active=True,
        ),
    ]
    for d in discounts:
        db_session.add(d)
    await db_session.commit()

    response = await client.get("/api/v1/discounts", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_update_discount(client: AsyncClient, db_session: AsyncSession, admin_headers: dict):
    discount = Discount(
        code="UPDATE1",
        name="Original Name",
        discount_type=DiscountType.PERCENTAGE,
        value=10.0,
        valid_from=datetime.now(UTC),
        valid_to=datetime.now(UTC) + timedelta(days=30),
        is_active=True,
    )
    db_session.add(discount)
    await db_session.commit()

    response = await client.put(
        f"/api/v1/discounts/{discount.id}",
        json={"name": "Updated Name", "value": 15.0},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["value"] == 15.0


@pytest.mark.asyncio
async def test_validate_discount_valid(client: AsyncClient, db_session: AsyncSession):
    discount = Discount(
        code="VALID123",
        name="Valid Discount",
        discount_type=DiscountType.PERCENTAGE,
        value=10.0,
        valid_from=datetime.now(UTC) - timedelta(days=1),
        valid_to=datetime.now(UTC) + timedelta(days=30),
        max_uses=100,
        current_uses=0,
        is_active=True,
    )
    db_session.add(discount)
    await db_session.commit()

    response = await client.post(
        "/api/v1/discounts/validate",
        json={"code": "VALID123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["discount"]["code"] == "VALID123"


@pytest.mark.asyncio
async def test_validate_discount_expired(client: AsyncClient, db_session: AsyncSession):
    discount = Discount(
        code="EXPIRED1",
        name="Expired Discount",
        discount_type=DiscountType.PERCENTAGE,
        value=10.0,
        valid_from=datetime.now(UTC) - timedelta(days=60),
        valid_to=datetime.now(UTC) - timedelta(days=30),
        is_active=True,
    )
    db_session.add(discount)
    await db_session.commit()

    response = await client.post(
        "/api/v1/discounts/validate",
        json={"code": "EXPIRED1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is False
    assert "expired" in data["message"].lower()


@pytest.mark.asyncio
async def test_validate_discount_not_yet_valid(client: AsyncClient, db_session: AsyncSession):
    discount = Discount(
        code="FUTURE1",
        name="Future Discount",
        discount_type=DiscountType.PERCENTAGE,
        value=10.0,
        valid_from=datetime.now(UTC) + timedelta(days=30),
        valid_to=datetime.now(UTC) + timedelta(days=60),
        is_active=True,
    )
    db_session.add(discount)
    await db_session.commit()

    response = await client.post(
        "/api/v1/discounts/validate",
        json={"code": "FUTURE1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is False


@pytest.mark.asyncio
async def test_validate_discount_usage_limit_reached(client: AsyncClient, db_session: AsyncSession):
    discount = Discount(
        code="MAXED1",
        name="Maxed Out Discount",
        discount_type=DiscountType.PERCENTAGE,
        value=10.0,
        valid_from=datetime.now(UTC) - timedelta(days=1),
        valid_to=datetime.now(UTC) + timedelta(days=30),
        max_uses=10,
        current_uses=10,
        is_active=True,
    )
    db_session.add(discount)
    await db_session.commit()

    response = await client.post(
        "/api/v1/discounts/validate",
        json={"code": "MAXED1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is False
    assert "limit" in data["message"].lower()


@pytest.mark.asyncio
async def test_validate_discount_invalid_code(client: AsyncClient):
    response = await client.post(
        "/api/v1/discounts/validate",
        json={"code": "NONEXISTENT"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is False
    assert "invalid" in data["message"].lower()


@pytest.mark.asyncio
async def test_deactivate_discount(
    client: AsyncClient, db_session: AsyncSession, admin_headers: dict
):
    discount = Discount(
        code="TODELETE",
        name="To Delete",
        discount_type=DiscountType.PERCENTAGE,
        value=10.0,
        valid_from=datetime.now(UTC),
        valid_to=datetime.now(UTC) + timedelta(days=30),
        is_active=True,
    )
    db_session.add(discount)
    await db_session.commit()

    response = await client.delete(f"/api/v1/discounts/{discount.id}", headers=admin_headers)
    assert response.status_code == 200

    # Verify it's deactivated
    response = await client.post(
        "/api/v1/discounts/validate",
        json={"code": "TODELETE"},
    )
    data = response.json()
    assert data["is_valid"] is False
