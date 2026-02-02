from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ev_charging import EVChargingStation
from src.models.membership import Membership
from src.models.parking import ParkingSpace
from src.models.payment import Payment
from src.models.session import ParkingSession
from src.schemas.report import DashboardSummary
from src.utils.constants import (
    MembershipStatus,
    PaymentStatus,
    SessionStatus,
    SpaceStatus,
    StationStatus,
)


async def get_dashboard_summary(db: AsyncSession) -> DashboardSummary:
    result = await db.execute(select(func.count(ParkingSpace.id)))
    total_spaces = result.scalar() or 0

    result = await db.execute(
        select(func.count(ParkingSpace.id)).where(ParkingSpace.status == SpaceStatus.OCCUPIED)
    )
    current_occupancy = result.scalar() or 0

    occupancy_rate = (current_occupancy / total_spaces * 100) if total_spaces > 0 else 0

    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=UTC)
    today_end = datetime.combine(date.today(), datetime.max.time()).replace(tzinfo=UTC)

    result = await db.execute(
        select(func.sum(Payment.total_amount)).where(
            Payment.status == PaymentStatus.COMPLETED,
            Payment.paid_at >= today_start,
            Payment.paid_at <= today_end,
        )
    )
    today_revenue = result.scalar() or 0

    result = await db.execute(
        select(func.count(ParkingSession.id)).where(
            ParkingSession.entry_time >= today_start,
            ParkingSession.entry_time <= today_end,
        )
    )
    today_entries = result.scalar() or 0

    result = await db.execute(
        select(func.count(ParkingSession.id)).where(
            ParkingSession.exit_time >= today_start,
            ParkingSession.exit_time <= today_end,
        )
    )
    today_exits = result.scalar() or 0

    result = await db.execute(
        select(func.count(ParkingSession.id)).where(ParkingSession.status == SessionStatus.ACTIVE)
    )
    active_sessions = result.scalar() or 0

    result = await db.execute(
        select(func.count(Payment.id)).where(Payment.status == PaymentStatus.PENDING)
    )
    pending_payments = result.scalar() or 0

    result = await db.execute(
        select(func.count(Membership.id)).where(Membership.status == MembershipStatus.ACTIVE)
    )
    active_memberships = result.scalar() or 0

    result = await db.execute(select(func.count(EVChargingStation.id)))
    ev_stations_total = result.scalar() or 0

    result = await db.execute(
        select(func.count(EVChargingStation.id)).where(
            EVChargingStation.status == StationStatus.AVAILABLE
        )
    )
    ev_stations_available = result.scalar() or 0

    return DashboardSummary(
        current_occupancy=current_occupancy,
        total_spaces=total_spaces,
        occupancy_rate=round(occupancy_rate, 2),
        today_revenue=float(today_revenue),
        today_entries=today_entries,
        today_exits=today_exits,
        active_sessions=active_sessions,
        pending_payments=pending_payments,
        active_memberships=active_memberships,
        ev_stations_available=ev_stations_available,
        ev_stations_total=ev_stations_total,
    )
