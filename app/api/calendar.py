from datetime import date
from fastapi import APIRouter, HTTPException, Depends, Query, status
from app.models.calendar import (
    CalendarSettingsCreate,
    CalendarSettingsResponse,
    AvailabilityGeneralUpdate,
    AvailabilityGeneralResponse,
    AvailabilityOverrideCreate,
    AvailabilityOverrideResponse,
    PublicAvailabilityResponse,
    BookingCreate,
    BookingResponse,
)
from app.services import calendar_service
from app.core.config import get_settings
from app.core.dependencies import get_current_user, get_current_admin

router = APIRouter(prefix="/calendar", tags=["Calendar"])


# ═══════════════════════════════════════════════════
#  Settings (Admin)
# ═══════════════════════════════════════════════════

@router.post("/settings", response_model=CalendarSettingsResponse)
async def upsert_calendar_settings(
    payload: CalendarSettingsCreate,
    admin: dict = Depends(get_current_admin),
):
    data = payload.model_dump(exclude_none=False)
    return calendar_service.upsert_settings(data)


@router.put("/settings", response_model=CalendarSettingsResponse)
async def update_calendar_settings(
    payload: CalendarSettingsCreate,
    admin: dict = Depends(get_current_admin),
):
    data = payload.model_dump(exclude_none=False)
    return calendar_service.upsert_settings(data)


@router.get("/settings", response_model=CalendarSettingsResponse)
async def get_calendar_settings(admin: dict = Depends(get_current_admin)):
    settings = calendar_service.get_settings()
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar settings not configured yet",
        )
    return settings


# ═══════════════════════════════════════════════════
#  General Availability (Admin)
# ═══════════════════════════════════════════════════

@router.get("/availability", response_model=AvailabilityGeneralResponse)
async def get_general_availability(admin: dict = Depends(get_current_admin)):
    days = calendar_service.get_general_availability()
    return {"days": days}


@router.put("/availability", response_model=AvailabilityGeneralResponse)
async def update_general_availability(
    payload: AvailabilityGeneralUpdate,
    admin: dict = Depends(get_current_admin),
):
    days_data = [d.model_dump() for d in payload.days]
    updated = calendar_service.upsert_general_availability(days_data)
    return {"days": updated}


# ═══════════════════════════════════════════════════
#  Availability Overrides (Admin)
# ═══════════════════════════════════════════════════

@router.get("/availability/overrides", response_model=list[AvailabilityOverrideResponse])
async def list_overrides(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    admin: dict = Depends(get_current_admin),
):
    return calendar_service.get_availability_overrides(date_from, date_to)


@router.post(
    "/availability/overrides",
    response_model=AvailabilityOverrideResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_or_update_override(
    payload: AvailabilityOverrideCreate,
    admin: dict = Depends(get_current_admin),
):
    data = payload.model_dump(mode="json")
    return calendar_service.upsert_availability_override(data)


@router.delete("/availability/overrides/{override_date}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_override(
    override_date: str,
    admin: dict = Depends(get_current_admin),
):
    success = calendar_service.delete_availability_override(override_date)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Override not found",
        )


# ═══════════════════════════════════════════════════
#  Public Availability (Authenticated Users)
# ═══════════════════════════════════════════════════

@router.get("/availability/public", response_model=PublicAvailabilityResponse)
async def get_public_availability(
    date_from: date = Query(...),
    date_to: date = Query(...),
    current_user: dict = Depends(get_current_user),
):
    if (date_to - date_from).days > 90:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range too large (max 90 days)",
        )
    return calendar_service.get_public_availability(date_from, date_to)


# ═══════════════════════════════════════════════════
#  Bookings – User
# ═══════════════════════════════════════════════════

@router.post("/bookings", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingCreate,
    current_user: dict = Depends(get_current_user),
):
    result = calendar_service.create_booking(
        booking_date=payload.booking_date,
        start_time_str=payload.start_time,
        end_time_str=payload.end_time,
        user_id=current_user["id"],
        notes=payload.notes,
    )
    if isinstance(result, str):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result,
        )
    return result


@router.get("/bookings/mine", response_model=list[BookingResponse])
async def list_my_bookings(current_user: dict = Depends(get_current_user)):
    return calendar_service.get_user_bookings(current_user["id"])


@router.get("/my-bookings", response_model=list[BookingResponse])
async def list_my_bookings_alias(current_user: dict = Depends(get_current_user)):
    """Alias kept for backward compatibility."""
    return calendar_service.get_user_bookings(current_user["id"])


@router.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_booking_by_id(
    booking_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Cancel a booking. Admins can cancel any, users only their own."""
    app_settings = get_settings()
    is_admin = current_user["username"] == app_settings.admin_username
    if is_admin:
        success = calendar_service.cancel_booking(booking_id)
    else:
        success = calendar_service.cancel_booking(booking_id, user_id=current_user["id"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel this booking",
        )


# ═══════════════════════════════════════════════════
#  Bookings – Admin
# ═══════════════════════════════════════════════════

@router.get("/bookings", response_model=list[dict])
async def list_all_bookings(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    admin: dict = Depends(get_current_admin),
):
    return calendar_service.get_all_bookings(
        date_from=date_from, date_to=date_to, status_filter=status_filter
    )
