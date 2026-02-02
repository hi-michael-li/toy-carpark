"""
End-to-end tests for complete user journeys.
These tests simulate real-world scenarios from start to finish.
"""
from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import get_password_hash
from src.models.ev_charging import EVChargingStation
from src.models.membership import MembershipPlan
from src.models.parking import Level, ParkingSpace, Zone
from src.models.payment import Discount, Rate
from src.models.user import User
from src.models.vehicle import VehicleType
from src.utils.constants import (
    ChargerType,
    DiscountType,
    RateType,
    SpaceStatus,
    StationStatus,
    UserRole,
)


@pytest.fixture
async def setup_full_carpark(db_session: AsyncSession):
    """Setup a complete car park with all infrastructure."""
    # Vehicle types
    car_type = VehicleType(name="Car", size_category="medium")
    motorcycle_type = VehicleType(name="Motorcycle", size_category="small")
    ev_type = VehicleType(name="Electric Vehicle", size_category="medium")
    db_session.add_all([car_type, motorcycle_type, ev_type])
    await db_session.flush()

    # Parking structure
    level = Level(name="Ground Floor", floor_number=0, is_underground=False)
    db_session.add(level)
    await db_session.flush()

    zone_a = Zone(level_id=level.id, name="Zone A", total_spaces=20, color_code="#FF0000")
    zone_b = Zone(level_id=level.id, name="Zone B - EV", total_spaces=10, color_code="#00FF00")
    db_session.add_all([zone_a, zone_b])
    await db_session.flush()

    # Regular parking spaces
    for i in range(20):
        space = ParkingSpace(
            zone_id=zone_a.id,
            space_number=f"A-{i+1:03d}",
            floor=0,
            status=SpaceStatus.AVAILABLE,
        )
        db_session.add(space)

    # EV charging spaces
    ev_spaces = []
    for i in range(10):
        space = ParkingSpace(
            zone_id=zone_b.id,
            space_number=f"EV-{i+1:03d}",
            floor=0,
            status=SpaceStatus.AVAILABLE,
            is_ev_charging=True,
        )
        db_session.add(space)
        ev_spaces.append(space)
    await db_session.flush()

    # EV charging stations (5 of 10 EV spaces have chargers)
    for space in ev_spaces[:5]:
        station = EVChargingStation(
            space_id=space.id,
            charger_type=ChargerType.LEVEL2,
            connector_type="J1772",
            power_kw=7.2,
            status=StationStatus.AVAILABLE,
            price_per_kwh=0.30,
            installed_at=date.today(),
        )
        db_session.add(station)
    await db_session.flush()

    # Rates
    hourly_rate = Rate(
        name="Standard Hourly",
        rate_type=RateType.HOURLY,
        amount=5.0,
        grace_period_minutes=0,  # No grace period for testing
        effective_from=datetime.now(UTC) - timedelta(days=30),
        is_active=True,
    )
    daily_rate = Rate(
        name="Daily Maximum",
        rate_type=RateType.DAILY,
        amount=25.0,
        effective_from=datetime.now(UTC) - timedelta(days=30),
        is_active=True,
    )
    db_session.add_all([hourly_rate, daily_rate])

    # Discounts
    promo_discount = Discount(
        code="WELCOME10",
        name="Welcome 10% Off",
        discount_type=DiscountType.PERCENTAGE,
        value=10.0,
        valid_from=datetime.now(UTC) - timedelta(days=1),
        valid_to=datetime.now(UTC) + timedelta(days=30),
        max_uses=100,
        is_active=True,
    )
    db_session.add(promo_discount)

    # Membership plans
    basic_plan = MembershipPlan(
        name="Basic Monthly",
        description="40 hours included per month",
        duration_months=1,
        price=50.0,
        vehicle_limit=1,
        included_hours=40,
        discount_percentage=0,
        is_active=True,
    )
    premium_plan = MembershipPlan(
        name="Premium Monthly",
        description="Unlimited parking + EV charging",
        duration_months=1,
        price=150.0,
        vehicle_limit=2,
        included_hours=None,
        discount_percentage=20,
        ev_charging_included=True,
        priority_reservation=True,
        is_active=True,
    )
    db_session.add_all([basic_plan, premium_plan])

    # Operator user
    operator = User(
        email="operator@carpark.com",
        hashed_password=get_password_hash("operator123"),
        full_name="Car Park Operator",
        role=UserRole.OPERATOR,
    )
    db_session.add(operator)

    # Admin user
    admin = User(
        email="admin@carpark.com",
        hashed_password=get_password_hash("admin123"),
        full_name="Admin User",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)

    await db_session.commit()

    return {
        "car_type": car_type,
        "ev_type": ev_type,
        "zone_a": zone_a,
        "zone_b": zone_b,
        "basic_plan": basic_plan,
        "premium_plan": premium_plan,
    }


@pytest.fixture
async def operator_headers(client: AsyncClient, setup_full_carpark: dict) -> dict:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "operator@carpark.com", "password": "operator123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def admin_headers(client: AsyncClient, setup_full_carpark: dict) -> dict:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@carpark.com", "password": "admin123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestCustomerParkingJourney:
    """Test complete parking journey for a walk-in customer."""

    @pytest.mark.asyncio
    async def test_complete_parking_flow(
        self,
        client: AsyncClient,
        operator_headers: dict,
        setup_full_carpark: dict,
    ):
        """
        Journey: Customer arrives → Parks → Pays → Exits
        """
        # Step 1: Customer registers (optional but common)
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "customer@example.com",
                "password": "customer123",
                "full_name": "John Customer",
                "phone": "+1234567890",
            },
        )
        assert register_response.status_code == 200
        customer_token = register_response.json()["access_token"]
        customer_headers = {"Authorization": f"Bearer {customer_token}"}

        # Step 2: Customer registers their vehicle
        car_type = setup_full_carpark["car_type"]
        vehicle_response = await client.post(
            "/api/v1/vehicles",
            json={
                "license_plate": "ABC123",
                "vehicle_type_id": car_type.id,
                "make": "Toyota",
                "model": "Camry",
                "color": "Silver",
            },
            headers=customer_headers,
        )
        assert vehicle_response.status_code == 200
        vehicle_response.json()

        # Step 3: Vehicle arrives - operator processes entry
        entry_response = await client.post(
            "/api/v1/sessions/entry",
            json={"license_plate": "ABC123", "entry_gate": "Main Entrance"},
            headers=operator_headers,
        )
        assert entry_response.status_code == 200
        entry_data = entry_response.json()
        ticket_number = entry_data["ticket_number"]
        session_id = entry_data["session"]["id"]

        # Verify space was assigned
        assert entry_data["space_assigned"] is not None

        # Step 4: Customer checks their session status (by ticket)
        session_response = await client.get(
            f"/api/v1/sessions/ticket/{ticket_number}",
            headers=operator_headers,
        )
        assert session_response.status_code == 200
        assert session_response.json()["status"] == "active"

        # Step 5: Before leaving, customer checks the fee
        fee_response = await client.get(
            f"/api/v1/sessions/{session_id}/calculate-fee",
            headers=operator_headers,
        )
        assert fee_response.status_code == 200
        fee_data = fee_response.json()
        total_fee = fee_data["total"]

        # Step 6: Customer validates at exit - not paid yet
        validate_response = await client.post(
            "/api/v1/payments/validate-exit",
            json={"ticket_number": ticket_number},
        )
        assert validate_response.status_code == 200
        assert validate_response.json()["is_paid"] is False
        assert validate_response.json()["can_exit"] is False

        # Step 7: Customer pays
        payment_response = await client.post(
            "/api/v1/payments",
            json={
                "session_id": session_id,
                "payment_method": "card",
                "amount": total_fee + 10,  # Slightly more to cover any timing differences
            },
            headers=customer_headers,
        )
        assert payment_response.status_code == 200
        assert payment_response.json()["status"] == "completed"

        # Step 8: Customer validates again - should be able to exit
        validate_response = await client.post(
            "/api/v1/payments/validate-exit",
            json={"ticket_number": ticket_number},
        )
        assert validate_response.status_code == 200
        assert validate_response.json()["is_paid"] is True
        assert validate_response.json()["can_exit"] is True

        # Step 9: Operator processes exit
        exit_response = await client.post(
            "/api/v1/sessions/exit",
            json={"ticket_number": ticket_number, "exit_gate": "Exit A"},
            headers=operator_headers,
        )
        assert exit_response.status_code == 200


class TestReservationJourney:
    """Test complete reservation flow."""

    @pytest.mark.asyncio
    async def test_reservation_to_checkin_flow(
        self,
        client: AsyncClient,
        operator_headers: dict,
        setup_full_carpark: dict,
    ):
        """
        Journey: Customer reserves → Arrives → Checks in → Parks → Pays → Exits
        """
        # Step 1: Customer registers
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "reserved@example.com",
                "password": "reserved123",
                "full_name": "Reserved Customer",
            },
        )
        customer_token = register_response.json()["access_token"]
        customer_headers = {"Authorization": f"Bearer {customer_token}"}

        # Step 2: Register vehicle
        car_type = setup_full_carpark["car_type"]
        vehicle_response = await client.post(
            "/api/v1/vehicles",
            json={"license_plate": "RSV001", "vehicle_type_id": car_type.id},
            headers=customer_headers,
        )
        vehicle_id = vehicle_response.json()["id"]

        # Step 3: Check availability
        start_time = datetime.now(UTC) + timedelta(hours=1)
        end_time = start_time + timedelta(hours=3)
        zone_id = setup_full_carpark["zone_a"].id

        availability_response = await client.get(
            "/api/v1/reservations/availability",
            params={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "zone_id": zone_id,
            },
        )
        assert availability_response.status_code == 200
        assert availability_response.json()["total_available"] > 0

        # Step 4: Make reservation
        reservation_response = await client.post(
            "/api/v1/reservations",
            json={
                "vehicle_id": vehicle_id,
                "zone_id": zone_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "special_requests": "Near entrance please",
            },
            headers=customer_headers,
        )
        assert reservation_response.status_code == 200
        reservation_data = reservation_response.json()
        confirmation_number = reservation_data["confirmation_number"]
        reservation_id = reservation_data["reservation"]["id"]

        # Step 5: Customer can look up their reservation
        lookup_response = await client.get(
            f"/api/v1/reservations/confirm/{confirmation_number}",
        )
        assert lookup_response.status_code == 200
        assert lookup_response.json()["status"] == "confirmed"

        # Step 6: Customer arrives and checks in
        checkin_response = await client.post(
            f"/api/v1/reservations/{reservation_id}/check-in",
            headers=customer_headers,
        )
        assert checkin_response.status_code == 200
        session_id = checkin_response.json()["session_id"]

        # Step 7: Verify a parking session was created
        session_response = await client.get(
            f"/api/v1/sessions/{session_id}",
            headers=operator_headers,
        )
        assert session_response.status_code == 200
        assert session_response.json()["status"] == "active"


class TestMembershipJourney:
    """Test membership subscription and usage."""

    @pytest.mark.asyncio
    async def test_membership_subscription_flow(
        self,
        client: AsyncClient,
        setup_full_carpark: dict,
    ):
        """
        Journey: Customer subscribes → Registers vehicle → Uses membership benefits
        """
        # Step 1: Customer registers
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "member@example.com",
                "password": "member123",
                "full_name": "Premium Member",
            },
        )
        member_token = register_response.json()["access_token"]
        member_headers = {"Authorization": f"Bearer {member_token}"}

        # Step 2: Browse membership plans
        plans_response = await client.get("/api/v1/memberships/plans")
        assert plans_response.status_code == 200
        plans = plans_response.json()
        assert len(plans) >= 2

        # Find premium plan
        premium_plan = next(p for p in plans if p["name"] == "Premium Monthly")

        # Step 3: Subscribe to premium plan
        subscribe_response = await client.post(
            "/api/v1/memberships",
            json={
                "plan_id": premium_plan["id"],
                "payment_method": "card",
                "auto_renew": True,
            },
            headers=member_headers,
        )
        assert subscribe_response.status_code == 200
        membership = subscribe_response.json()["membership"]
        membership_id = membership["id"]

        # Step 4: Check membership status
        membership_response = await client.get(
            f"/api/v1/memberships/{membership_id}",
            headers=member_headers,
        )
        assert membership_response.status_code == 200
        assert membership_response.json()["status"] == "active"

        # Step 5: Check usage stats
        usage_response = await client.get(
            f"/api/v1/memberships/{membership_id}/usage",
            headers=member_headers,
        )
        assert usage_response.status_code == 200
        usage = usage_response.json()
        assert usage["used_hours"] == 0
        assert usage["days_remaining"] > 0


class TestEVChargingJourney:
    """Test complete EV charging flow."""

    @pytest.mark.asyncio
    async def test_ev_parking_and_charging_flow(
        self,
        client: AsyncClient,
        operator_headers: dict,
        setup_full_carpark: dict,
    ):
        """
        Journey: EV arrives → Parks at EV spot → Charges → Pays → Exits
        """
        # Step 1: Customer registers
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "evdriver@example.com",
                "password": "evdriver123",
                "full_name": "EV Driver",
            },
        )
        ev_token = register_response.json()["access_token"]
        ev_headers = {"Authorization": f"Bearer {ev_token}"}

        # Step 2: Register EV
        ev_type = setup_full_carpark["ev_type"]
        vehicle_response = await client.post(
            "/api/v1/vehicles",
            json={
                "license_plate": "EV001",
                "vehicle_type_id": ev_type.id,
                "make": "Tesla",
                "model": "Model 3",
                "is_ev": True,
            },
            headers=ev_headers,
        )
        vehicle_id = vehicle_response.json()["id"]

        # Step 3: Check available EV charging stations
        stations_response = await client.get("/api/v1/ev/stations?available_only=true")
        assert stations_response.status_code == 200
        stations = stations_response.json()
        assert len(stations) > 0
        station_id = stations[0]["id"]

        # Step 4: Vehicle entry
        entry_response = await client.post(
            "/api/v1/sessions/entry",
            json={"license_plate": "EV001", "entry_gate": "EV Entrance"},
            headers=operator_headers,
        )
        assert entry_response.status_code == 200
        session_data = entry_response.json()
        parking_session_id = session_data["session"]["id"]
        ticket_number = session_data["ticket_number"]

        # Step 5: Start charging session
        charging_response = await client.post(
            "/api/v1/ev/charging/start",
            json={
                "station_id": station_id,
                "vehicle_id": vehicle_id,
                "parking_session_id": parking_session_id,
                "max_power_requested": 7.2,
            },
            headers=ev_headers,
        )
        assert charging_response.status_code == 200
        charging_session_id = charging_response.json()["id"]
        assert charging_response.json()["status"] == "charging"

        # Step 6: Stop charging when done
        stop_response = await client.post(
            f"/api/v1/ev/charging/{charging_session_id}/stop",
            headers=ev_headers,
        )
        assert stop_response.status_code == 200
        stop_data = stop_response.json()
        assert stop_data["session"]["status"] == "completed"
        assert stop_data["energy_used"] >= 0
        assert stop_data["cost"] >= 0

        # Step 7: Pay for parking
        fee_response = await client.get(
            f"/api/v1/sessions/{parking_session_id}/calculate-fee",
            headers=operator_headers,
        )
        total_fee = fee_response.json()["total"]

        payment_response = await client.post(
            "/api/v1/payments",
            json={
                "session_id": parking_session_id,
                "payment_method": "card",
                "amount": total_fee + 10,
            },
            headers=ev_headers,
        )
        assert payment_response.status_code == 200

        # Step 8: Exit
        exit_response = await client.post(
            "/api/v1/sessions/exit",
            json={"ticket_number": ticket_number, "exit_gate": "EV Exit"},
            headers=operator_headers,
        )
        assert exit_response.status_code == 200


class TestDiscountJourney:
    """Test using discount codes during payment."""

    @pytest.mark.asyncio
    async def test_payment_with_discount(
        self,
        client: AsyncClient,
        operator_headers: dict,
        setup_full_carpark: dict,
    ):
        """
        Journey: Park → Apply discount code → Pay reduced amount → Exit
        """
        # Step 1: Customer registers
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "discount@example.com",
                "password": "discount123",
                "full_name": "Discount User",
            },
        )
        user_token = register_response.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}

        # Step 2: Vehicle entry
        entry_response = await client.post(
            "/api/v1/sessions/entry",
            json={"license_plate": "DISC001", "entry_gate": "Main"},
            headers=operator_headers,
        )
        session_id = entry_response.json()["session"]["id"]
        ticket_number = entry_response.json()["ticket_number"]

        # Step 3: Validate discount code
        validate_response = await client.post(
            "/api/v1/discounts/validate",
            json={"code": "WELCOME10", "session_id": session_id},
        )
        assert validate_response.status_code == 200
        discount_data = validate_response.json()
        assert discount_data["is_valid"] is True

        # Step 4: Calculate fee
        fee_response = await client.get(
            f"/api/v1/sessions/{session_id}/calculate-fee",
            headers=operator_headers,
        )
        base_fee = fee_response.json()["total"]

        # Step 5: Pay with discount
        payment_response = await client.post(
            "/api/v1/payments",
            json={
                "session_id": session_id,
                "payment_method": "card",
                "discount_code": "WELCOME10",
                "amount": base_fee,  # Full amount, discount applied server-side
            },
            headers=user_headers,
        )
        assert payment_response.status_code == 200
        payment_data = payment_response.json()
        assert payment_data["discount_amount"] > 0  # Discount was applied

        # Step 6: Exit
        exit_response = await client.post(
            "/api/v1/sessions/exit",
            json={"ticket_number": ticket_number},
            headers=operator_headers,
        )
        assert exit_response.status_code == 200


class TestAdminDashboardJourney:
    """Test admin monitoring the car park."""

    @pytest.mark.asyncio
    async def test_admin_monitors_carpark(
        self,
        client: AsyncClient,
        operator_headers: dict,
        admin_headers: dict,
        setup_full_carpark: dict,
    ):
        """
        Journey: Admin checks dashboard → Views occupancy → Manages rates
        """
        # Create some activity first
        for i in range(3):
            await client.post(
                "/api/v1/sessions/entry",
                json={"license_plate": f"ADMIN{i:03d}", "entry_gate": "Gate A"},
                headers=operator_headers,
            )

        # Step 1: Admin checks dashboard
        dashboard_response = await client.get(
            "/api/v1/reports/dashboard",
            headers=admin_headers,
        )
        assert dashboard_response.status_code == 200
        dashboard = dashboard_response.json()
        assert dashboard["active_sessions"] >= 3
        assert dashboard["total_spaces"] > 0

        # Step 2: Admin checks zone availability
        zone_id = setup_full_carpark["zone_a"].id
        availability_response = await client.get(
            f"/api/v1/zones/{zone_id}/availability",
        )
        assert availability_response.status_code == 200
        availability = availability_response.json()
        assert availability["occupied"] >= 3

        # Step 3: Admin creates a new rate
        rate_response = await client.post(
            "/api/v1/rates",
            json={
                "name": "Weekend Rate",
                "rate_type": "hourly",
                "amount": 3.0,
                "grace_period_minutes": 20,
                "effective_from": datetime.now(UTC).isoformat(),
            },
            headers=admin_headers,
        )
        assert rate_response.status_code == 200

        # Step 4: Admin lists all rates
        rates_response = await client.get("/api/v1/rates")
        assert rates_response.status_code == 200
        rates = rates_response.json()
        assert len(rates) >= 3  # Original 2 + new one
