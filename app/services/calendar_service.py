"""
Calendar service – availability-based booking system.

Tables used:
  - calendar_settings        (singleton settings row)
  - admin_availability_general   (7 rows, one per weekday)
  - admin_availability_overrides (per-date overrides)
  - bookings                 (user bookings with direct date/time)
"""

from datetime import date, datetime, timedelta, timezone, time as dt_time
from app.db.connection import get_supabase_client


# ───────────────────────────────────────
#  Settings
# ───────────────────────────────────────

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


# ───────────────────────────────────────
#  General Availability (weekly)
# ───────────────────────────────────────

def get_general_availability() -> list[dict]:
    """Return 7 rows sorted by day_of_week (0=Mon … 6=Sun)."""
    client = get_supabase_client()
    result = (
        client.table("admin_availability_general")
        .select("*")
        .order("day_of_week")
        .execute()
    )
    rows = result.data or []
    # Ensure we always return 7 days; seed missing ones
    existing = {r["day_of_week"]: r for r in rows}
    out = []
    for d in range(7):
        if d in existing:
            row = existing[d]
            # Normalise time values returned by Postgres (e.g. "08:00:00") to "HH:MM"
            row["start_time"] = _normalise_time(row.get("start_time", "08:00"))
            row["end_time"] = _normalise_time(row.get("end_time", "17:00"))
            out.append(row)
        else:
            out.append({
                "day_of_week": d,
                "is_enabled": d < 5,
                "start_time": "08:00",
                "end_time": "17:00",
            })
    return out


def upsert_general_availability(days: list[dict]) -> list[dict]:
    """Upsert all 7 weekday rows."""
    client = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()
    for day in days:
        day["updated_at"] = now
        # Use upsert with on_conflict
        client.table("admin_availability_general").upsert(
            day, on_conflict="day_of_week"
        ).execute()
    return get_general_availability()


# ───────────────────────────────────────
#  Availability Overrides (per-date)
# ───────────────────────────────────────

def get_availability_overrides(
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict]:
    client = get_supabase_client()
    query = (
        client.table("admin_availability_overrides")
        .select("*")
        .order("override_date")
    )
    if date_from:
        query = query.gte("override_date", date_from.isoformat())
    if date_to:
        query = query.lte("override_date", date_to.isoformat())
    result = query.execute()
    rows = result.data or []
    for r in rows:
        if r.get("start_time"):
            r["start_time"] = _normalise_time(r["start_time"])
        if r.get("end_time"):
            r["end_time"] = _normalise_time(r["end_time"])
    return rows


def upsert_availability_override(data: dict) -> dict:
    client = get_supabase_client()
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = (
        client.table("admin_availability_overrides")
        .upsert(data, on_conflict="override_date")
        .execute()
    )
    row = result.data[0]
    if row.get("start_time"):
        row["start_time"] = _normalise_time(row["start_time"])
    if row.get("end_time"):
        row["end_time"] = _normalise_time(row["end_time"])
    return row


def delete_availability_override(override_date: str) -> bool:
    client = get_supabase_client()
    result = (
        client.table("admin_availability_overrides")
        .delete()
        .eq("override_date", override_date)
        .execute()
    )
    return bool(result.data)


# ───────────────────────────────────────
#  Public Availability (for users)
# ───────────────────────────────────────

def get_public_availability(
    date_from: date,
    date_to: date,
) -> dict:
    """
    Combine general weekly schedule + per-date overrides into a
    day-by-day availability list for the requested date range.
    """
    general = get_general_availability()
    overrides = get_availability_overrides(date_from, date_to)
    settings = get_settings()
    allow_outside = (
        settings.get("allow_booking_outside_availability", False)
        if settings
        else False
    )

    override_map = {o["override_date"]: o for o in overrides}

    days = []
    current = date_from
    while current <= date_to:
        iso = current.isoformat()
        # 0=Monday … 6=Sunday  (Python weekday() is already Mon=0)
        dow = current.weekday()
        gen = general[dow] if dow < len(general) else None

        if iso in override_map:
            ovr = override_map[iso]
            days.append({
                "date": iso,
                "is_available": not ovr["is_closed"],
                "start_time": ovr.get("start_time"),
                "end_time": ovr.get("end_time"),
                "is_override": True,
                "notes": ovr.get("notes"),
            })
        elif gen:
            days.append({
                "date": iso,
                "is_available": gen.get("is_enabled", False),
                "start_time": gen["start_time"] if gen.get("is_enabled") else None,
                "end_time": gen["end_time"] if gen.get("is_enabled") else None,
                "is_override": False,
                "notes": None,
            })
        else:
            days.append({
                "date": iso,
                "is_available": False,
                "start_time": None,
                "end_time": None,
                "is_override": False,
                "notes": None,
            })
        current += timedelta(days=1)

    # Build override response objects
    override_responses = []
    for o in overrides:
        override_responses.append({
            "id": o["id"],
            "override_date": o["override_date"],
            "is_closed": o["is_closed"],
            "start_time": o.get("start_time"),
            "end_time": o.get("end_time"),
            "notes": o.get("notes"),
            "created_at": o["created_at"],
            "updated_at": o["updated_at"],
        })

    general_schema = []
    for g in general:
        general_schema.append({
            "day_of_week": g["day_of_week"],
            "is_enabled": g.get("is_enabled", False),
            "start_time": g["start_time"],
            "end_time": g["end_time"],
        })

    return {
        "general": general_schema,
        "overrides": override_responses,
        "days": days,
        "allow_booking_outside_availability": allow_outside,
    }


# ───────────────────────────────────────
#  Bookings
# ───────────────────────────────────────

def _get_day_availability(booking_date: date) -> dict | None:
    """Get effective availability for a single date."""
    client = get_supabase_client()
    # Check override first
    ovr = (
        client.table("admin_availability_overrides")
        .select("*")
        .eq("override_date", booking_date.isoformat())
        .maybe_single()
        .execute()
    )
    if ovr and ovr.data:
        o = ovr.data
        if o["is_closed"]:
            return {"is_available": False}
        return {
            "is_available": True,
            "start_time": _normalise_time(o["start_time"]) if o.get("start_time") else None,
            "end_time": _normalise_time(o["end_time"]) if o.get("end_time") else None,
        }

    # Fall back to general
    dow = booking_date.weekday()
    gen = (
        client.table("admin_availability_general")
        .select("*")
        .eq("day_of_week", dow)
        .maybe_single()
        .execute()
    )
    if gen and gen.data:
        g = gen.data
        return {
            "is_available": g.get("is_enabled", False),
            "start_time": _normalise_time(g["start_time"]) if g.get("is_enabled") else None,
            "end_time": _normalise_time(g["end_time"]) if g.get("is_enabled") else None,
        }

    return {"is_available": False}


def create_booking(
    booking_date: date,
    start_time_str: str,
    end_time_str: str,
    user_id: str,
    notes: str | None = None,
) -> dict | str:
    """
    Create a booking.  Returns the booking dict on success,
    or an error-message string on failure.
    """
    client = get_supabase_client()

    # Parse times
    try:
        sh, sm = map(int, start_time_str.split(":"))
        eh, em = map(int, end_time_str.split(":"))
        start_t = dt_time(sh, sm)
        end_t = dt_time(eh, em)
    except Exception:
        return "Invalid time format"

    if start_t >= end_t:
        return "start_time must be before end_time"

    settings = get_settings()

    # Min booking notice
    if settings and settings.get("min_booking_notice_minutes"):
        now = datetime.now(timezone.utc)
        booking_start_dt = datetime.combine(
            booking_date, start_t, tzinfo=timezone.utc
        )
        min_notice = timedelta(minutes=settings["min_booking_notice_minutes"])
        if booking_start_dt - now < min_notice:
            return "Booking too close to start time"

    # Max advance days
    if settings and settings.get("max_advance_booking_days"):
        now = datetime.now(timezone.utc)
        booking_start_dt = datetime.combine(
            booking_date, start_t, tzinfo=timezone.utc
        )
        max_advance = timedelta(days=settings["max_advance_booking_days"])
        if booking_start_dt - now > max_advance:
            return "Booking too far in the future"

    # Check availability constraints
    allow_outside = (
        settings.get("allow_booking_outside_availability", False)
        if settings
        else False
    )

    if not allow_outside:
        avail = _get_day_availability(booking_date)
        if not avail or not avail.get("is_available"):
            return "No availability on this date"
        avail_start = avail.get("start_time")
        avail_end = avail.get("end_time")
        if avail_start and avail_end:
            ash, asm = map(int, avail_start.split(":"))
            aeh, aem = map(int, avail_end.split(":"))
            if start_t < dt_time(ash, asm) or end_t > dt_time(aeh, aem):
                return "Booking outside available hours"

    # Check overlapping confirmed bookings
    existing = (
        client.table("bookings")
        .select("id, start_time, end_time")
        .eq("booking_date", booking_date.isoformat())
        .eq("status", "confirmed")
        .execute()
    )
    for b in (existing.data or []):
        b_start = b.get("start_time", "")
        b_end = b.get("end_time", "")
        if not b_start or not b_end:
            continue
        b_start = _normalise_time(b_start)
        b_end = _normalise_time(b_end)
        bsh, bsm = map(int, b_start.split(":"))
        beh, bem = map(int, b_end.split(":"))
        b_start_t = dt_time(bsh, bsm)
        b_end_t = dt_time(beh, bem)
        if start_t < b_end_t and end_t > b_start_t:
            return "Time overlaps with an existing booking"

    booking_data = {
        "user_id": user_id,
        "booking_date": booking_date.isoformat(),
        "start_time": start_time_str,
        "end_time": end_time_str,
        "notes": notes,
        "status": "confirmed",
    }
    result = client.table("bookings").insert(booking_data).execute()
    if result.data:
        row = result.data[0]
        row["start_time"] = _normalise_time(row.get("start_time", start_time_str))
        row["end_time"] = _normalise_time(row.get("end_time", end_time_str))
        return row
    return "Failed to create booking"


def get_user_bookings(user_id: str) -> list[dict]:
    client = get_supabase_client()
    result = (
        client.table("bookings")
        .select("*, users(username)")
        .eq("user_id", user_id)
        .order("booking_date", desc=True)
        .execute()
    )
    bookings = result.data or []
    out = []
    for b in bookings:
        user_data = b.pop("users", None)
        b["username"] = user_data.get("username") if user_data else None
        if b.get("start_time"):
            b["start_time"] = _normalise_time(b["start_time"])
        if b.get("end_time"):
            b["end_time"] = _normalise_time(b["end_time"])
        out.append(b)
    return out


def get_all_bookings(
    date_from: date | None = None,
    date_to: date | None = None,
    status_filter: str | None = None,
) -> list[dict]:
    client = get_supabase_client()
    query = (
        client.table("bookings")
        .select("*, users(username, email)")
        .order("booking_date", desc=True)
    )

    if date_from:
        query = query.gte("booking_date", date_from.isoformat())
    if date_to:
        query = query.lte("booking_date", date_to.isoformat())
    if status_filter:
        query = query.eq("status", status_filter)

    result = query.execute()
    bookings = result.data or []

    out = []
    for b in bookings:
        user_data = b.pop("users", None)
        b["username"] = user_data.get("username") if user_data else None
        b["user_email"] = user_data.get("email") if user_data else None
        if b.get("start_time"):
            b["start_time"] = _normalise_time(b["start_time"])
        if b.get("end_time"):
            b["end_time"] = _normalise_time(b["end_time"])
        out.append(b)
    return out


def cancel_booking(booking_id: str, user_id: str | None = None) -> bool:
    client = get_supabase_client()
    query = (
        client.table("bookings")
        .select("*")
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
        b = booking.data
        if b.get("booking_date") and b.get("start_time"):
            start_str = _normalise_time(b["start_time"])
            sh, sm = map(int, start_str.split(":"))
            bd = date.fromisoformat(b["booking_date"])
            booking_start_dt = datetime.combine(
                bd, dt_time(sh, sm), tzinfo=timezone.utc
            )
            min_notice = timedelta(minutes=settings["cancellation_notice_minutes"])
            if booking_start_dt - now < min_notice:
                return False

    client.table("bookings").update({
        "status": "cancelled",
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", booking_id).execute()

    return True


# ───────────────────────────────────────
#  Helpers
# ───────────────────────────────────────

def _normalise_time(val: str) -> str:
    """Convert '08:00:00' or '08:00:00+00' to 'HH:MM'."""
    if not val:
        return val
    return val[:5]
