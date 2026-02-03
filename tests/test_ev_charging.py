from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import get_password_hash
from src.models.ev_charging import ChargingSession, EVChargingStation
from src.models.payment import Discount
from src.models.parking import Level, ParkingSpace, Zone
from src.models.session import ParkingSession
from src.models.user import User
from src.models.vehicle import Vehicle, VehicleType
from src.utils.constants import (
    ChargerType,
    ChargingStatus,
    DiscountType,
    SessionStatus,
    SpaceStatus,
    StationStatus,
    UserRole,
)

PROMO_CODE = "EVHALF4"
LEVEL2_SURCHARGE = 0.25
PROMO_HOURS = 4


def create_promo_discount() -> Discount:
    now = datetime.now(UTC)
    return Discount(
        code=PROMO_CODE,
        name="EV Promo",
        discount_type=DiscountType.PERCENTAGE,
        value=50,
        valid_from=now - timedelta(days=1),
        valid_to=now + timedelta(days=1),
        max_uses=None,
        current_uses=0,
        max_uses_per_user=10,
        min_duration_hours=None,
        partner_name="EV",
        is_active=True,
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
async def setup_ev_data(db_session: AsyncSession):
    """Setup EV charging infrastructure."""
    vehicle_type = VehicleType(name="EV", size_category="medium")
    db_session.add(vehicle_type)
    await db_session.flush()

    level = Level(name="Ground", floor_number=0)
    db_session.add(level)
    await db_session.flush()

    zone = Zone(level_id=level.id, name="EV Zone", total_spaces=10)
    db_session.add(zone)
    await db_session.flush()

    spaces = []
    for i in range(5):
        space = ParkingSpace(
            zone_id=zone.id,
            space_number=f"EV-{i+1:03d}",
            floor=0,
            status=SpaceStatus.AVAILABLE,
            is_ev_charging=True,
        )
        db_session.add(space)
        spaces.append(space)
    await db_session.flush()

    # Create some EV stations
    stations = []
    for i, space in enumerate(spaces[:3]):
        station = EVChargingStation(
            space_id=space.id,
            charger_type=ChargerType.LEVEL2 if i < 2 else ChargerType.DC_FAST,
            connector_type="J1772" if i < 2 else "CCS",
            power_kw=7.2 if i < 2 else 50.0,
            status=StationStatus.AVAILABLE,
            price_per_kwh=0.30,
            installed_at=date.today(),
        )
        db_session.add(station)
        stations.append(station)
    await db_session.flush()

    vehicle = Vehicle(license_plate="EV123", vehicle_type_id=vehicle_type.id, is_ev=True)
    db_session.add(vehicle)
    await db_session.commit()

    return {
        "vehicle_type": vehicle_type,
        "zone": zone,
        "spaces": spaces,
        "stations": stations,
        "vehicle": vehicle,
    }


@pytest.mark.asyncio
async def test_list_ev_stations(client: AsyncClient, setup_ev_data: dict):
    response = await client.get("/api/v1/ev/stations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_list_ev_stations_returns_list_type(client: AsyncClient, setup_ev_data: dict):
    response = await client.get("/api/v1/ev/stations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_available_ev_stations(
    client: AsyncClient, db_session: AsyncSession, setup_ev_data: dict
):
    # Mark one station as in use
    station = setup_ev_data["stations"][0]
    station.status = StationStatus.IN_USE
    await db_session.commit()

    response = await client.get("/api/v1/ev/stations?available_only=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_create_ev_station(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict,
    setup_ev_data: dict,
):
    # Use a space without a station
    space = setup_ev_data["spaces"][3]

    response = await client.post(
        "/api/v1/ev/stations",
        json={
            "space_id": space.id,
            "charger_type": "level2",
            "connector_type": "J1772",
            "power_kw": 11.0,
            "price_per_kwh": 0.35,
            "installed_at": date.today().isoformat(),
            "manufacturer": "ChargePoint",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["power_kw"] == 11.0
    assert data["connector_type"] == "J1772"


@pytest.mark.asyncio
async def test_update_ev_station(client: AsyncClient, admin_headers: dict, setup_ev_data: dict):
    station = setup_ev_data["stations"][0]

    response = await client.put(
        f"/api/v1/ev/stations/{station.id}",
        json={"price_per_kwh": 0.40, "status": "offline"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["price_per_kwh"] == 0.40
    assert data["status"] == "offline"


@pytest.mark.asyncio
async def test_start_charging_session(client: AsyncClient, auth_headers: dict, setup_ev_data: dict):
    station = setup_ev_data["stations"][0]
    vehicle = setup_ev_data["vehicle"]

    response = await client.post(
        "/api/v1/ev/charging/start",
        json={
            "station_id": station.id,
            "vehicle_id": vehicle.id,
            "max_power_requested": 7.2,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "charging"
    assert data["station_id"] == station.id
    assert data["vehicle_id"] == vehicle.id


@pytest.mark.asyncio
async def test_start_charging_unavailable_station(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, setup_ev_data: dict
):
    station = setup_ev_data["stations"][0]
    station.status = StationStatus.IN_USE
    await db_session.commit()

    vehicle = setup_ev_data["vehicle"]

    response = await client.post(
        "/api/v1/ev/charging/start",
        json={"station_id": station.id, "vehicle_id": vehicle.id},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_stop_charging_session(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, setup_ev_data: dict
):
    station = setup_ev_data["stations"][0]
    vehicle = setup_ev_data["vehicle"]

    # Start a charging session
    charging_session = ChargingSession(
        station_id=station.id,
        vehicle_id=vehicle.id,
        start_time=datetime.now(UTC) - timedelta(hours=1),
        status=ChargingStatus.CHARGING,
    )
    db_session.add(charging_session)
    station.status = StationStatus.IN_USE
    await db_session.commit()

    response = await client.post(
        f"/api/v1/ev/charging/{charging_session.id}/stop",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session"]["status"] == "completed"
    assert "energy_used" in data
    assert "cost" in data
    assert "duration_minutes" in data


@pytest.mark.asyncio
async def test_list_charging_sessions(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, setup_ev_data: dict
):
    station = setup_ev_data["stations"][0]
    vehicle = setup_ev_data["vehicle"]

    # Create charging sessions
    for i in range(3):
        session = ChargingSession(
            station_id=station.id,
            vehicle_id=vehicle.id,
            start_time=datetime.now(UTC) - timedelta(hours=i + 1),
            end_time=datetime.now(UTC) - timedelta(hours=i),
            energy_kwh=5.0 + i,
            cost=1.5 + i * 0.3,
            status=ChargingStatus.COMPLETED,
        )
        db_session.add(session)
    await db_session.commit()

    response = await client.get("/api/v1/ev/charging", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_list_charging_sessions_by_station(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, setup_ev_data: dict
):
    stations = setup_ev_data["stations"]
    vehicle = setup_ev_data["vehicle"]

    # Create sessions on different stations
    for _i, station in enumerate(stations[:2]):
        session = ChargingSession(
            station_id=station.id,
            vehicle_id=vehicle.id,
            start_time=datetime.now(UTC) - timedelta(hours=1),
            status=ChargingStatus.COMPLETED,
        )
        db_session.add(session)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/ev/charging?station_id={stations[0].id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_filter_stations_by_charger_type(client: AsyncClient, setup_ev_data: dict):
    response = await client.get("/api/v1/ev/stations?status=available")
    assert response.status_code == 200
    data = response.json()
    # All 3 stations should be available initially
    assert len(data) == 3


@pytest.mark.asyncio
async def test_stop_charging_promo_half_price_first_four_hours(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, setup_ev_data: dict
):
    station = setup_ev_data["stations"][0]
    vehicle = setup_ev_data["vehicle"]
    space = setup_ev_data["spaces"][0]

    parking_session = ParkingSession(
        vehicle_id=vehicle.id,
        space_id=space.id,
        entry_time=datetime.now(UTC) - timedelta(hours=2),
        ticket_number="TKT-PROMO-1",
        status=SessionStatus.ACTIVE,
    )
    db_session.add(parking_session)
    await db_session.flush()

    promo_discount = create_promo_discount()
    db_session.add(promo_discount)

    charging_session = ChargingSession(
        station_id=station.id,
        vehicle_id=vehicle.id,
        parking_session_id=parking_session.id,
        start_time=datetime.now(UTC) - timedelta(hours=2),
        status=ChargingStatus.CHARGING,
    )
    db_session.add(charging_session)
    station.status = StationStatus.IN_USE
    await db_session.commit()
    await db_session.refresh(charging_session)

    response = await client.post(
        f"/api/v1/ev/charging/{charging_session.id}/stop?p={PROMO_CODE}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()

    duration_minutes = data["duration_minutes"]
    hours = duration_minutes / 60
    promo_hours = min(PROMO_HOURS, hours)
    full_hours = max(0, hours - PROMO_HOURS)
    power_kw = float(station.power_kw)
    level2_rate = float(station.price_per_kwh) + LEVEL2_SURCHARGE
    expected_cost = round(
        (promo_hours * power_kw * 0.8 * level2_rate * 0.5)
        + (full_hours * power_kw * 0.8 * level2_rate),
        2,
    )
    assert data["cost"] == expected_cost


@pytest.mark.asyncio
async def test_stop_charging_promo_caps_after_four_hours(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, setup_ev_data: dict
):
    station = setup_ev_data["stations"][0]
    vehicle = setup_ev_data["vehicle"]
    space = setup_ev_data["spaces"][0]

    parking_session = ParkingSession(
        vehicle_id=vehicle.id,
        space_id=space.id,
        entry_time=datetime.now(UTC) - timedelta(hours=6),
        ticket_number="TKT-PROMO-2",
        status=SessionStatus.ACTIVE,
    )
    db_session.add(parking_session)
    await db_session.flush()

    promo_discount = create_promo_discount()
    db_session.add(promo_discount)

    charging_session = ChargingSession(
        station_id=station.id,
        vehicle_id=vehicle.id,
        parking_session_id=parking_session.id,
        start_time=datetime.now(UTC) - timedelta(hours=6),
        status=ChargingStatus.CHARGING,
    )
    db_session.add(charging_session)
    station.status = StationStatus.IN_USE
    await db_session.commit()
    await db_session.refresh(charging_session)

    response = await client.post(
        f"/api/v1/ev/charging/{charging_session.id}/stop?p={PROMO_CODE}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()

    duration_minutes = data["duration_minutes"]
    hours = duration_minutes / 60
    promo_hours = min(PROMO_HOURS, hours)
    full_hours = max(0, hours - PROMO_HOURS)
    power_kw = float(station.power_kw)
    level2_rate = float(station.price_per_kwh) + LEVEL2_SURCHARGE
    expected_cost = round(
        (promo_hours * power_kw * 0.8 * level2_rate * 0.5)
        + (full_hours * power_kw * 0.8 * level2_rate),
        2,
    )
    assert data["cost"] == expected_cost


@pytest.mark.asyncio
async def test_stop_charging_promo_ignored_for_non_ev_vehicle(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, setup_ev_data: dict
):
    station = setup_ev_data["stations"][0]
    vehicle_type = setup_ev_data["vehicle_type"]
    space = setup_ev_data["spaces"][0]

    non_ev_vehicle = Vehicle(
        license_plate="ICE123",
        vehicle_type_id=vehicle_type.id,
        is_ev=False,
    )
    db_session.add(non_ev_vehicle)
    await db_session.flush()

    promo_discount = create_promo_discount()
    db_session.add(promo_discount)

    parking_session = ParkingSession(
        vehicle_id=non_ev_vehicle.id,
        space_id=space.id,
        entry_time=datetime.now(UTC) - timedelta(hours=2),
        ticket_number="TKT-PROMO-3",
        status=SessionStatus.ACTIVE,
    )
    db_session.add(parking_session)
    await db_session.flush()

    charging_session = ChargingSession(
        station_id=station.id,
        vehicle_id=non_ev_vehicle.id,
        parking_session_id=parking_session.id,
        start_time=datetime.now(UTC) - timedelta(hours=2),
        status=ChargingStatus.CHARGING,
    )
    db_session.add(charging_session)
    station.status = StationStatus.IN_USE
    await db_session.commit()
    await db_session.refresh(charging_session)

    response = await client.post(
        f"/api/v1/ev/charging/{charging_session.id}/stop?p={PROMO_CODE}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()

    duration_minutes = data["duration_minutes"]
    hours = duration_minutes / 60
    power_kw = float(station.power_kw)
    level2_rate = float(station.price_per_kwh) + LEVEL2_SURCHARGE
    expected_cost = round(hours * power_kw * 0.8 * level2_rate, 2)
    assert data["cost"] == expected_cost


@pytest.mark.asyncio
async def test_stop_charging_promo_ignored_without_parking_session(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, setup_ev_data: dict
):
    station = setup_ev_data["stations"][0]
    vehicle = setup_ev_data["vehicle"]

    charging_session = ChargingSession(
        station_id=station.id,
        vehicle_id=vehicle.id,
        parking_session_id=None,
        start_time=datetime.now(UTC) - timedelta(hours=2),
        status=ChargingStatus.CHARGING,
    )
    db_session.add(charging_session)
    station.status = StationStatus.IN_USE
    promo_discount = create_promo_discount()
    db_session.add(promo_discount)
    await db_session.commit()
    await db_session.refresh(charging_session)

    response = await client.post(
        f"/api/v1/ev/charging/{charging_session.id}/stop?p={PROMO_CODE}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()

    duration_minutes = data["duration_minutes"]
    hours = duration_minutes / 60
    power_kw = float(station.power_kw)
    level2_rate = float(station.price_per_kwh) + LEVEL2_SURCHARGE
    expected_cost = round(hours * power_kw * 0.8 * level2_rate, 2)
    assert data["cost"] == expected_cost


@pytest.mark.asyncio
async def test_stop_charging_promo_ignored_for_non_ev_space(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, setup_ev_data: dict
):
    station = setup_ev_data["stations"][0]
    vehicle = setup_ev_data["vehicle"]
    zone = setup_ev_data["zone"]

    non_ev_space = ParkingSpace(
        zone_id=zone.id,
        space_number="S-100",
        floor=0,
        status=SpaceStatus.AVAILABLE,
        is_ev_charging=False,
    )
    db_session.add(non_ev_space)
    await db_session.flush()

    parking_session = ParkingSession(
        vehicle_id=vehicle.id,
        space_id=non_ev_space.id,
        entry_time=datetime.now(UTC) - timedelta(hours=2),
        ticket_number="TKT-PROMO-4",
        status=SessionStatus.ACTIVE,
    )
    db_session.add(parking_session)
    await db_session.flush()

    promo_discount = create_promo_discount()
    db_session.add(promo_discount)

    charging_session = ChargingSession(
        station_id=station.id,
        vehicle_id=vehicle.id,
        parking_session_id=parking_session.id,
        start_time=datetime.now(UTC) - timedelta(hours=2),
        status=ChargingStatus.CHARGING,
    )
    db_session.add(charging_session)
    station.status = StationStatus.IN_USE
    await db_session.commit()
    await db_session.refresh(charging_session)

    response = await client.post(
        f"/api/v1/ev/charging/{charging_session.id}/stop?p={PROMO_CODE}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()

    duration_minutes = data["duration_minutes"]
    hours = duration_minutes / 60
    power_kw = float(station.power_kw)
    level2_rate = float(station.price_per_kwh) + LEVEL2_SURCHARGE
    expected_cost = round(hours * power_kw * 0.8 * level2_rate, 2)
    assert data["cost"] == expected_cost


@pytest.mark.asyncio
async def test_stop_charging_dc_fast_uses_station_price(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, setup_ev_data: dict
):
    station = setup_ev_data["stations"][2]
    vehicle = setup_ev_data["vehicle"]

    charging_session = ChargingSession(
        station_id=station.id,
        vehicle_id=vehicle.id,
        start_time=datetime.now(UTC) - timedelta(hours=1),
        status=ChargingStatus.CHARGING,
    )
    db_session.add(charging_session)
    station.status = StationStatus.IN_USE
    await db_session.commit()
    await db_session.refresh(charging_session)

    response = await client.post(
        f"/api/v1/ev/charging/{charging_session.id}/stop",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()

    duration_minutes = data["duration_minutes"]
    hours = duration_minutes / 60
    power_kw = float(station.power_kw)
    expected_cost = round(hours * power_kw * 0.8 * float(station.price_per_kwh), 2)
    assert data["cost"] == expected_cost
