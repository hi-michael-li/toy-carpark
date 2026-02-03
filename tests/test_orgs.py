import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import get_password_hash
from src.models.user import User
from src.utils.constants import UserRole


@pytest.fixture
async def admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    admin = User(
        email="orgadmin@example.com",
        hashed_password=get_password_hash("adminpass123"),
        full_name="Org Admin",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.commit()

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "orgadmin@example.com", "password": "adminpass123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def user_headers(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "orguser@example.com",
            "password": "userpass123",
            "full_name": "Org User",
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_and_list_orgs(
    client: AsyncClient, admin_headers: dict, user_headers: dict
):
    create = await client.post(
        "/api/v1/orgs",
        json={"name": "Acme Org", "notes": "test"},
        headers=admin_headers,
    )
    assert create.status_code == 200

    list_resp = await client.get("/api/v1/orgs", headers=user_headers)
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_add_member_to_multiple_orgs(
    client: AsyncClient, admin_headers: dict, user_headers: dict
):
    org1 = await client.post(
        "/api/v1/orgs",
        json={"name": "Org One"},
        headers=admin_headers,
    )
    org2 = await client.post(
        "/api/v1/orgs",
        json={"name": "Org Two"},
        headers=admin_headers,
    )
    assert org1.status_code == 200
    assert org2.status_code == 200

    org1_id = org1.json()["id"]
    org2_id = org2.json()["id"]

    add1 = await client.post(f"/api/v1/orgs/{org1_id}/members", headers=user_headers)
    add2 = await client.post(f"/api/v1/orgs/{org2_id}/members", headers=user_headers)
    assert add1.status_code == 200
    assert add2.status_code == 200

    members1 = await client.get(f"/api/v1/orgs/{org1_id}/members", headers=user_headers)
    members2 = await client.get(f"/api/v1/orgs/{org2_id}/members", headers=user_headers)
    assert members1.status_code == 200
    assert members2.status_code == 200
    assert len(members1.json()) == 1
    assert len(members2.json()) == 1


@pytest.mark.asyncio
async def test_create_plan_and_set_plan(
    client: AsyncClient, admin_headers: dict, user_headers: dict
):
    org = await client.post(
        "/api/v1/orgs",
        json={"name": "Billing Org"},
        headers=admin_headers,
    )
    assert org.status_code == 200
    org_id = org.json()["id"]

    plan = await client.post(
        f"/api/v1/orgs/{org_id}/plans",
        json={"name": "Gold", "price": 99.0, "max_users": 10},
        headers=admin_headers,
    )
    assert plan.status_code == 200
    plan_id = plan.json()["id"]

    set_plan = await client.post(
        f"/api/v1/orgs/{org_id}/set-plan",
        params={"plan_id": plan_id},
        headers=admin_headers,
    )
    assert set_plan.status_code == 200
    assert set_plan.json()["billing_plan_id"] == plan_id


@pytest.mark.asyncio
async def test_duplicate_membership_allowed(
    client: AsyncClient, admin_headers: dict, user_headers: dict
):
    org = await client.post(
        "/api/v1/orgs",
        json={"name": "Dup Org"},
        headers=admin_headers,
    )
    assert org.status_code == 200
    org_id = org.json()["id"]

    add1 = await client.post(f"/api/v1/orgs/{org_id}/members", headers=user_headers)
    add2 = await client.post(f"/api/v1/orgs/{org_id}/members", headers=user_headers)
    assert add1.status_code == 200
    assert add2.status_code == 200

    members = await client.get(f"/api/v1/orgs/{org_id}/members", headers=user_headers)
    assert members.status_code == 200
    assert len(members.json()) == 2


@pytest.mark.asyncio
async def test_cross_org_plan_assignment_allowed(
    client: AsyncClient, admin_headers: dict, user_headers: dict
):
    org1 = await client.post(
        "/api/v1/orgs",
        json={"name": "Plan Org A"},
        headers=admin_headers,
    )
    org2 = await client.post(
        "/api/v1/orgs",
        json={"name": "Plan Org B"},
        headers=admin_headers,
    )
    assert org1.status_code == 200
    assert org2.status_code == 200
    org1_id = org1.json()["id"]
    org2_id = org2.json()["id"]

    plan = await client.post(
        f"/api/v1/orgs/{org1_id}/plans",
        json={"name": "Silver", "price": 49.0},
        headers=admin_headers,
    )
    assert plan.status_code == 200
    plan_id = plan.json()["id"]

    set_plan = await client.post(
        f"/api/v1/orgs/{org2_id}/set-plan",
        params={"plan_id": plan_id},
        headers=admin_headers,
    )
    assert set_plan.status_code == 200
    assert set_plan.json()["billing_plan_id"] == plan_id


@pytest.mark.asyncio
async def test_regular_user_can_add_other_user_to_org(
    client: AsyncClient, admin_headers: dict, user_headers: dict
):
    org = await client.post(
        "/api/v1/orgs",
        json={"name": "User Managed Org"},
        headers=admin_headers,
    )
    assert org.status_code == 200
    org_id = org.json()["id"]

    other_user = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "orguser2@example.com",
            "password": "userpass456",
            "full_name": "Org User 2",
        },
    )
    assert other_user.status_code == 200
    other_user_id = other_user.json()["user"]["id"]

    add_member = await client.post(
        f"/api/v1/orgs/{org_id}/members",
        params={"user_id": other_user_id},
        headers=user_headers,
    )
    assert add_member.status_code == 200

    members = await client.get(f"/api/v1/orgs/{org_id}/members", headers=user_headers)
    assert members.status_code == 200
    assert len(members.json()) == 1
