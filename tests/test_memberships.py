from datetime import date

import pytest
from dateutil.relativedelta import relativedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import get_password_hash
from src.models.membership import Membership, MembershipPlan
from src.models.user import User
from src.utils.constants import MembershipStatus, UserRole


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
async def membership_plans(db_session: AsyncSession) -> list[MembershipPlan]:
    plans = [
        MembershipPlan(
            name="Basic",
            description="Basic monthly plan",
            duration_months=1,
            price=50.0,
            vehicle_limit=1,
            included_hours=40,
            discount_percentage=0,
            is_active=True,
        ),
        MembershipPlan(
            name="Premium",
            description="Premium monthly plan",
            duration_months=1,
            price=100.0,
            vehicle_limit=2,
            included_hours=None,  # Unlimited
            discount_percentage=10,
            priority_reservation=True,
            ev_charging_included=True,
            is_active=True,
        ),
        MembershipPlan(
            name="Annual",
            description="Annual plan",
            duration_months=12,
            price=500.0,
            vehicle_limit=1,
            included_hours=500,
            discount_percentage=15,
            is_active=True,
        ),
    ]
    for plan in plans:
        db_session.add(plan)
    await db_session.commit()
    return plans


@pytest.mark.asyncio
async def test_list_membership_plans(
    client: AsyncClient, db_session: AsyncSession, membership_plans: list
):
    response = await client.get("/api/v1/memberships/plans")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_create_membership_plan(client: AsyncClient, admin_headers: dict):
    response = await client.post(
        "/api/v1/memberships/plans",
        json={
            "name": "Corporate",
            "description": "Corporate plan for businesses",
            "duration_months": 12,
            "price": 1000.0,
            "vehicle_limit": 10,
            "included_hours": 1000,
            "discount_percentage": 20,
            "priority_reservation": True,
            "ev_charging_included": True,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Corporate"
    assert data["price"] == 1000.0
    assert data["vehicle_limit"] == 10


@pytest.mark.asyncio
async def test_update_membership_plan(
    client: AsyncClient, db_session: AsyncSession, admin_headers: dict, membership_plans: list
):
    plan = membership_plans[0]

    response = await client.put(
        f"/api/v1/memberships/plans/{plan.id}",
        json={"name": "Basic Plus", "price": 60.0},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Basic Plus"
    assert data["price"] == 60.0


@pytest.mark.asyncio
async def test_subscribe_to_membership(
    client: AsyncClient, auth_headers: dict, membership_plans: list
):
    plan = membership_plans[0]

    response = await client.post(
        "/api/v1/memberships",
        json={
            "plan_id": plan.id,
            "payment_method": "card",
            "auto_renew": True,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["membership"]["status"] == "active"
    assert data["membership"]["plan_id"] == plan.id
    assert data["membership"]["auto_renew"] is True


@pytest.mark.asyncio
async def test_subscribe_duplicate_fails(
    client: AsyncClient, auth_headers: dict, membership_plans: list
):
    plan = membership_plans[0]

    # First subscription
    await client.post(
        "/api/v1/memberships",
        json={"plan_id": plan.id, "payment_method": "card"},
        headers=auth_headers,
    )

    # Second subscription should fail
    response = await client.post(
        "/api/v1/memberships",
        json={"plan_id": plan.id, "payment_method": "card"},
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_list_memberships(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    test_user: dict,
    membership_plans: list,
):
    user_id = test_user["user"]["id"]
    plan = membership_plans[0]

    membership = Membership(
        user_id=user_id,
        plan_id=plan.id,
        start_date=date.today(),
        end_date=date.today() + relativedelta(months=1),
        status=MembershipStatus.ACTIVE,
    )
    db_session.add(membership)
    await db_session.commit()

    response = await client.get("/api/v1/memberships", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_membership_usage(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    test_user: dict,
    membership_plans: list,
):
    user_id = test_user["user"]["id"]
    plan = membership_plans[0]  # Has 40 included hours

    membership = Membership(
        user_id=user_id,
        plan_id=plan.id,
        start_date=date.today(),
        end_date=date.today() + relativedelta(months=1),
        status=MembershipStatus.ACTIVE,
        used_hours=10.0,
    )
    db_session.add(membership)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/memberships/{membership.id}/usage",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["included_hours"] == 40
    assert data["used_hours"] == 10.0
    assert data["remaining_hours"] == 30.0


@pytest.mark.asyncio
async def test_cancel_membership(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    test_user: dict,
    membership_plans: list,
):
    user_id = test_user["user"]["id"]
    plan = membership_plans[0]

    membership = Membership(
        user_id=user_id,
        plan_id=plan.id,
        start_date=date.today(),
        end_date=date.today() + relativedelta(months=1),
        status=MembershipStatus.ACTIVE,
    )
    db_session.add(membership)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/memberships/{membership.id}/cancel",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"


@pytest.mark.asyncio
async def test_renew_membership(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    test_user: dict,
    membership_plans: list,
):
    user_id = test_user["user"]["id"]
    plan = membership_plans[0]

    original_end_date = date.today() + relativedelta(days=5)
    membership = Membership(
        user_id=user_id,
        plan_id=plan.id,
        start_date=date.today(),
        end_date=original_end_date,
        status=MembershipStatus.ACTIVE,
    )
    db_session.add(membership)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/memberships/{membership.id}/renew",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    # End date should be extended by plan duration
    new_end = date.fromisoformat(data["membership"]["end_date"])
    expected_end = original_end_date + relativedelta(months=plan.duration_months)
    assert new_end == expected_end


@pytest.mark.asyncio
async def test_subscribe_to_inactive_plan_fails(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict
):
    plan = MembershipPlan(
        name="Inactive Plan",
        duration_months=1,
        price=50.0,
        is_active=False,
    )
    db_session.add(plan)
    await db_session.commit()

    response = await client.post(
        "/api/v1/memberships",
        json={"plan_id": plan.id, "payment_method": "card"},
        headers=auth_headers,
    )
    assert response.status_code == 422
