from datetime import date, datetime, timedelta, timezone, time
from app.db.connection import get_supabase_client


def get_settings() -> dict | None:
    client = get_supabase_client()
    result = (
        client.table("calendar_settings")
        .select("*")
        .limit(1)
        .maybe_single()
        .execute()
    )
    return result.data if result else None


def upsert_settings(data: dict) -> dict:
    client = get_supabase_client()
    existing = get_settings()
    data["updated_at"] = datetime.now(timezone.utc).isoformat()

    if existing:
        result = (
            client.table("calendar_settings")
            .update(data)
            .eq("id", existing["id"])
            .execute()
        )
    else:
        result = client.table("calendar_settings").insert(data).execute()

    return result.data[0]


def create_slot(slot_data: dict) -> dict:
    client = get_supabase_client()
    result = client.table("calendar_slots").insert(slot_data).execute()
    return result.data[0]


def create_batch_slots(
    start_date: date,
    end_date: date,
    start_time_str: str,
    end_time_str: str,
    exclude_weekends: bool,
    admin_id: str,
) -> list[dict]:
    settings = get_settings()
    slot_duration = settings["slot_duration_minutes"] if settings and settings.get("slot_duration_minutes") else None
    tz = settings["timezone"] if settings else "UTC"

    slots_to_create = []
    current_date = start_date

    while current_date <= end_date:
        if exclude_weekends and current_date.weekday() >= 5:
            current_date += timedelta(days=1)
            continue

        start_h, start_m = map(int, start_time_str.split(":"))
        end_h, end_m = map(int, end_time_str.split(":"))

        if slot_duration:
            current_start = datetime(
                current_date.year, current_date.month, current_date.day,
                start_h, start_m, tzinfo=timezone.utc,
            )
            day_end = datetime(
                current_date.year, current_date.month, current_date.day,
                end_h, end_m, tzinfo=timezone.utc,
            )
            while current_start + timedelta(minutes=slot_duration) <= day_end:
                slot_end = current_start + timedelta(minutes=slot_duration)
                slots_to_create.append({
                    "date": current_date.isoformat(),
                    "start_time": current_start.isoformat(),
                    "end_time": slot_end.isoformat(),
                    "is_available": True,
                    "created_by": admin_id,
                })
                current_start = slot_end
        else:
            slot_start = datetime(
                current_date.year, current_date.month, current_date.day,
                start_h, start_m, tzinfo=timezone.utc,
            )
            slot_end = datetime(
                current_date.year, current_date.month, current_date.day,
                end_h, end_m, tzinfo=timezone.utc,
            )
            slots_to_create.append({
                "date": current_date.isoformat(),
                "start_time": slot_start.isoformat(),
                "end_time": slot_end.isoformat(),
                "is_available": True,
                "created_by": admin_id,
            })

        current_date += timedelta(days=1)

    if not slots_to_create:
        return []

    client = get_supabase_client()
    result = client.table("calendar_slots").insert(slots_to_create).execute()
    return result.data


def get_slot_by_id(slot_id: str) -> dict | None:
    client = get_supabase_client()
    result = (
        client.table("calendar_slots")
        .select("*")
        .eq("id", slot_id)
        .maybe_single()
        .execute()
    )
    return result.data if result else None


def update_slot(slot_id: str, data: dict) -> dict | None:
    client = get_supabase_client()
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = (
        client.table("calendar_slots")
        .update(data)
        .eq("id", slot_id)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def delete_slot(slot_id: str) -> bool:
    client = get_supabase_client()
    confirmed_bookings = (
        client.table("bookings")
        .select("id")
        .eq("slot_id", slot_id)
        .eq("status", "confirmed")
        .execute()
    )
    if confirmed_bookings.data:
        return False

    client.table("calendar_slots").delete().eq("id", slot_id).execute()
    return True


def get_all_slots(
    date_from: date | None = None,
    date_to: date | None = None,
    available_only: bool = False,
) -> list[dict]:
    client = get_supabase_client()
    query = client.table("calendar_slots").select("*").order("date").order("start_time")

    if date_from:
        query = query.gte("date", date_from.isoformat())
    if date_to:
        query = query.lte("date", date_to.isoformat())
    if available_only:
        query = query.eq("is_available", True)

    result = query.execute()
    return result.data


def get_available_slots(
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict]:
    client = get_supabase_client()
    query = (
        client.table("calendar_slots")
        .select("*")
        .eq("is_available", True)
        .order("date")
        .order("start_time")
    )

    if date_from:
        query = query.gte("date", date_from.isoformat())
    if date_to:
        query = query.lte("date", date_to.isoformat())

    slots = query.execute().data

    available = []
    for slot in slots:
        booking = (
            client.table("bookings")
            .select("id")
            .eq("slot_id", slot["id"])
            .eq("status", "confirmed")
            .maybe_single()
            .execute()
        )
        if not booking or booking.data is None:
            available.append(slot)

    return available


def create_booking(slot_id: str, user_id: str, notes: str | None = None) -> dict | None:
    client = get_supabase_client()

    slot = get_slot_by_id(slot_id)
    if slot is None or not slot["is_available"]:
        return None

    existing_booking = (
        client.table("bookings")
        .select("id")
        .eq("slot_id", slot_id)
        .eq("status", "confirmed")
        .maybe_single()
        .execute()
    )
    if existing_booking and existing_booking.data:
        return None

    settings = get_settings()
    if settings and settings.get("min_booking_notice_minutes"):
        now = datetime.now(timezone.utc)
        slot_start = datetime.fromisoformat(slot["start_time"])
        if slot_start.tzinfo is None:
            slot_start = slot_start.replace(tzinfo=timezone.utc)
        min_notice = timedelta(minutes=settings["min_booking_notice_minutes"])
        if slot_start - now < min_notice:
            return None

    if settings and settings.get("max_advance_booking_days"):
        now = datetime.now(timezone.utc)
        slot_start = datetime.fromisoformat(slot["start_time"])
        if slot_start.tzinfo is None:
            slot_start = slot_start.replace(tzinfo=timezone.utc)
        max_advance = timedelta(days=settings["max_advance_booking_days"])
        if slot_start - now > max_advance:
            return None

    booking_data = {
        "slot_id": slot_id,
        "user_id": user_id,
        "notes": notes,
    }
    result = client.table("bookings").insert(booking_data).execute()
    return result.data[0] if result.data else None


def get_user_bookings(user_id: str) -> list[dict]:
    client = get_supabase_client()
    result = (
        client.table("bookings")
        .select("*, calendar_slots(*)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


def get_all_bookings(
    date_from: date | None = None,
    date_to: date | None = None,
    status_filter: str | None = None,
) -> list[dict]:
    client = get_supabase_client()
    query = (
        client.table("bookings")
        .select("*, calendar_slots(*), users(username, email)")
        .order("created_at", desc=True)
    )

    if status_filter:
        query = query.eq("status", status_filter)

    result = query.execute()

    bookings = result.data
    if date_from or date_to:
        filtered = []
        for b in bookings:
            slot = b.get("calendar_slots")
            if slot:
                slot_date = slot.get("date")
                if date_from and slot_date < date_from.isoformat():
                    continue
                if date_to and slot_date > date_to.isoformat():
                    continue
            filtered.append(b)
        bookings = filtered

    return bookings


def cancel_booking(booking_id: str, user_id: str | None = None) -> bool:
    client = get_supabase_client()
    query = (
        client.table("bookings")
        .select("*, calendar_slots(*)")
        .eq("id", booking_id)
        .eq("status", "confirmed")
    )
    if user_id:
        query = query.eq("user_id", user_id)

    booking = query.maybe_single().execute()
    if not booking or booking.data is None:
        return False

    settings = get_settings()
    if settings and not settings.get("allow_cancellation", True):
        return False

    if user_id and settings and settings.get("cancellation_notice_minutes"):
        now = datetime.now(timezone.utc)
        slot = booking.data.get("calendar_slots", {})
        slot_start = datetime.fromisoformat(slot["start_time"])
        if slot_start.tzinfo is None:
            slot_start = slot_start.replace(tzinfo=timezone.utc)
        min_notice = timedelta(minutes=settings["cancellation_notice_minutes"])
        if slot_start - now < min_notice:
            return False

    client.table("bookings").update({
        "status": "cancelled",
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", booking_id).execute()

    return True
