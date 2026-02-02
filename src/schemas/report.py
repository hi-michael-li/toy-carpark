from datetime import date, datetime

from src.schemas.common import BaseSchema


class OccupancyData(BaseSchema):
    timestamp: datetime
    total_spaces: int
    occupied: int
    available: int
    occupancy_rate: float


class OccupancyReport(BaseSchema):
    data: list[OccupancyData]
    period_start: datetime
    period_end: datetime
    average_occupancy: float
    peak_occupancy: float
    peak_time: datetime | None = None


class RevenueData(BaseSchema):
    date: date
    amount: float
    transaction_count: int
    payment_method_breakdown: dict[str, float]


class RevenueReport(BaseSchema):
    data: list[RevenueData]
    period_start: date
    period_end: date
    total_revenue: float
    average_daily_revenue: float
    comparison_previous_period: float | None = None


class PeakHourData(BaseSchema):
    hour: int
    average_entries: float
    average_exits: float
    average_occupancy: float


class PeakHoursReport(BaseSchema):
    hourly_data: list[PeakHourData]
    busiest_entry_hours: list[int]
    busiest_exit_hours: list[int]


class VehicleTypeDistribution(BaseSchema):
    vehicle_type: str
    count: int
    percentage: float


class VehicleTypeReport(BaseSchema):
    distribution: list[VehicleTypeDistribution]
    total_vehicles: int


class DurationData(BaseSchema):
    date: date
    average_minutes: float
    median_minutes: float
    total_sessions: int


class DurationReport(BaseSchema):
    average_minutes: float
    by_day: list[DurationData]


class MembershipStats(BaseSchema):
    active_memberships: int
    new_memberships: int
    churned_memberships: int
    membership_revenue: float
    retention_rate: float


class DashboardSummary(BaseSchema):
    current_occupancy: int
    total_spaces: int
    occupancy_rate: float
    today_revenue: float
    today_entries: int
    today_exits: int
    active_sessions: int
    pending_payments: int
    active_memberships: int
    ev_stations_available: int
    ev_stations_total: int


class ExportRequest(BaseSchema):
    report_type: str
    start_date: date
    end_date: date
    format: str = "csv"
