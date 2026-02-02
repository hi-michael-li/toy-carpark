from enum import Enum


class UserRole(str, Enum):
    CUSTOMER = "customer"
    OPERATOR = "operator"
    ADMIN = "admin"


class OperatorRole(str, Enum):
    ATTENDANT = "attendant"
    SUPERVISOR = "supervisor"
    MANAGER = "manager"


class SizeCategory(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    EXTRA_LARGE = "extra_large"


class SpaceType(str, Enum):
    STANDARD = "standard"
    COMPACT = "compact"
    HANDICAPPED = "handicapped"
    EV_CHARGING = "ev_charging"
    MOTORCYCLE = "motorcycle"


class SpaceStatus(str, Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    CASH = "cash"
    CARD = "card"
    MOBILE = "mobile"
    ACCOUNT_BALANCE = "account_balance"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class RateType(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    FLAT = "flat"


class DiscountType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    FREE_HOURS = "free_hours"


class ReservationStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class MembershipStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class ChargerType(str, Enum):
    LEVEL1 = "level1"
    LEVEL2 = "level2"
    DC_FAST = "dc_fast"


class StationStatus(str, Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    FAULTED = "faulted"
    OFFLINE = "offline"


class ChargingStatus(str, Enum):
    STARTED = "started"
    CHARGING = "charging"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"


class NotificationType(str, Enum):
    SESSION_EXPIRING = "session_expiring"
    PAYMENT_DUE = "payment_due"
    RESERVATION_REMINDER = "reservation_reminder"
    MEMBERSHIP_EXPIRING = "membership_expiring"
    GENERAL = "general"
