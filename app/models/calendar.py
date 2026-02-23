from pydantic import BaseModel
from datetime import date, time, datetime


class CalendarSettingsCreate(BaseModel):
    slot_duration_minutes: int | None = None
    default_start_time: str = "08:00"
    default_end_time: str = "17:00"
    timezone: str = "UTC"
    min_booking_notice_minutes: int | None = None
    max_advance_booking_days: int | None = None
    allow_cancellation: bool = True
    cancellation_notice_minutes: int | None = None


class CalendarSettingsResponse(BaseModel):
    id: str
    slot_duration_minutes: int | None = None
    default_start_time: str
    default_end_time: str
    timezone: str
    min_booking_notice_minutes: int | None = None
    max_advance_booking_days: int | None = None
    allow_cancellation: bool
    cancellation_notice_minutes: int | None = None
    created_at: datetime
    updated_at: datetime


class SlotCreate(BaseModel):
    date: date
    start_time: datetime
    end_time: datetime
    notes: str | None = None


class SlotBatchCreate(BaseModel):
    start_date: date
    end_date: date
    start_time: str
    end_time: str
    exclude_weekends: bool = True


class SlotUpdate(BaseModel):
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_available: bool | None = None
    notes: str | None = None


class SlotResponse(BaseModel):
    id: str
    date: date
    start_time: datetime
    end_time: datetime
    is_available: bool
    notes: str | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime


class BookingCreate(BaseModel):
    slot_id: str
    notes: str | None = None


class BookingResponse(BaseModel):
    id: str
    slot_id: str
    user_id: str
    status: str
    cancelled_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    slot: SlotResponse | None = None


class BookingWithUser(BookingResponse):
    username: str | None = None
    user_email: str | None = None
