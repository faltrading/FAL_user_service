from pydantic import BaseModel, field_validator
from datetime import date, datetime

# ──────────────────────────────────────────────
#  Calendar Settings
# ──────────────────────────────────────────────

class CalendarSettingsCreate(BaseModel):
    default_start_time: str = "08:00"
    default_end_time: str = "17:00"
    timezone: str = "UTC"
    min_booking_notice_minutes: int | None = None
    max_advance_booking_days: int | None = None
    allow_cancellation: bool = True
    cancellation_notice_minutes: int | None = None
    allow_booking_outside_availability: bool = False


class CalendarSettingsResponse(BaseModel):
    id: str
    default_start_time: str
    default_end_time: str
    timezone: str
    min_booking_notice_minutes: int | None = None
    max_advance_booking_days: int | None = None
    allow_cancellation: bool
    cancellation_notice_minutes: int | None = None
    allow_booking_outside_availability: bool = False
    created_at: datetime
    updated_at: datetime


# ──────────────────────────────────────────────
#  General Availability (weekly schedule)
# ──────────────────────────────────────────────

class AvailabilityDaySchema(BaseModel):
    day_of_week: int  # 0=Monday … 6=Sunday
    is_enabled: bool = True
    start_time: str = "08:00"  # HH:MM
    end_time: str = "17:00"

    @field_validator("day_of_week")
    @classmethod
    def validate_day(cls, v: int) -> int:
        if v < 0 or v > 6:
            raise ValueError("day_of_week must be 0-6")
        return v


class AvailabilityGeneralUpdate(BaseModel):
    days: list[AvailabilityDaySchema]

    @field_validator("days")
    @classmethod
    def validate_seven_days(cls, v: list) -> list:
        if len(v) != 7:
            raise ValueError("Must provide exactly 7 days (Monday-Sunday)")
        return v


class AvailabilityGeneralResponse(BaseModel):
    days: list[AvailabilityDaySchema]


# ──────────────────────────────────────────────
#  Availability Overrides (per-date)
# ──────────────────────────────────────────────

class AvailabilityOverrideCreate(BaseModel):
    override_date: date
    is_closed: bool = False
    start_time: str | None = None  # HH:MM – required when is_closed=False
    end_time: str | None = None
    notes: str | None = None


class AvailabilityOverrideResponse(BaseModel):
    id: str
    override_date: date
    is_closed: bool
    start_time: str | None = None
    end_time: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


# ──────────────────────────────────────────────
#  Public Availability (returned to users)
# ──────────────────────────────────────────────

class PublicDayAvailability(BaseModel):
    date: date
    is_available: bool
    start_time: str | None = None  # HH:MM
    end_time: str | None = None
    is_override: bool = False
    notes: str | None = None


class PublicAvailabilityResponse(BaseModel):
    general: list[AvailabilityDaySchema]
    overrides: list[AvailabilityOverrideResponse]
    days: list[PublicDayAvailability]
    allow_booking_outside_availability: bool


# ──────────────────────────────────────────────
#  Bookings (no longer slot-based)
# ──────────────────────────────────────────────

class BookingCreate(BaseModel):
    booking_date: date
    start_time: str  # HH:MM
    end_time: str    # HH:MM
    notes: str | None = None


class BookingResponse(BaseModel):
    id: str
    user_id: str
    booking_date: date
    start_time: str
    end_time: str
    status: str
    cancelled_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    username: str | None = None
