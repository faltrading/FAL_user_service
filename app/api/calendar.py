from datetime import date
from fastapi import APIRouter, HTTPException, Depends, Query, status
from app.models.calendar import (
    CalendarSettingsCreate,
    CalendarSettingsResponse,
    SlotCreate,
    SlotBatchCreate,
    SlotUpdate,
    SlotResponse,
    BookingCreate,
    BookingResponse,
)
from app.services import calendar_service
from app.core.config import get_settings
from app.core.dependencies import get_current_user, get_current_admin

router = APIRouter(prefix="/calendar", tags=["Calendar"])


@router.post("/settings", response_model=CalendarSettingsResponse)
async def upsert_calendar_settings(
    payload: CalendarSettingsCreate,
    admin: dict = Depends(get_current_admin),
):
    data = payload.model_dump(exclude_none=False)
    result = calendar_service.upsert_settings(data)
    return result


@router.put("/settings", response_model=CalendarSettingsResponse)
async def update_calendar_settings(
    payload: CalendarSettingsCreate,
    admin: dict = Depends(get_current_admin),
):
    data = payload.model_dump(exclude_none=False)
    result = calendar_service.upsert_settings(data)
    return result


@router.get("/settings", response_model=CalendarSettingsResponse)
async def get_calendar_settings(admin: dict = Depends(get_current_admin)):
    settings = calendar_service.get_settings()
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar settings not configured yet",
        )
    return settings


@router.post("/slots", response_model=SlotResponse, status_code=status.HTTP_201_CREATED)
async def create_slot(
    payload: SlotCreate,
    admin: dict = Depends(get_current_admin),
):
    slot_data = payload.model_dump(mode="json")
    slot_data["created_by"] = admin["id"]
    slot_data["is_available"] = True
    result = calendar_service.create_slot(slot_data)
    return result


@router.post("/slots/batch", response_model=list[SlotResponse], status_code=status.HTTP_201_CREATED)
async def create_batch_slots(
    payload: SlotBatchCreate,
    admin: dict = Depends(get_current_admin),
):
    result = calendar_service.create_batch_slots(
        start_date=payload.start_date,
        end_date=payload.end_date,
        start_time_str=payload.start_time,
        end_time_str=payload.end_time,
        exclude_weekends=payload.exclude_weekends,
        admin_id=admin["id"],
    )
    return result


@router.put("/slots/{slot_id}", response_model=SlotResponse)
async def update_slot(
    slot_id: str,
    payload: SlotUpdate,
    admin: dict = Depends(get_current_admin),
):
    existing = calendar_service.get_slot_by_id(slot_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slot not found",
        )

    update_data = payload.model_dump(exclude_none=True, mode="json")
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    result = calendar_service.update_slot(slot_id, update_data)
    return result


@router.delete("/slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slot(
    slot_id: str,
    admin: dict = Depends(get_current_admin),
):
    existing = calendar_service.get_slot_by_id(slot_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slot not found",
        )

    success = calendar_service.delete_slot(slot_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete slot with active bookings",
        )


@router.get("/slots", response_model=list[SlotResponse])
async def list_all_slots(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    available_only: bool = Query(False),
    admin: dict = Depends(get_current_admin),
):
    return calendar_service.get_all_slots(
        date_from=date_from, date_to=date_to, available_only=available_only
    )


@router.get("/available-slots", response_model=list[SlotResponse])
async def list_available_slots(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    current_user: dict = Depends(get_current_user),
):
    return calendar_service.get_available_slots(date_from=date_from, date_to=date_to)


@router.post("/bookings", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingCreate,
    current_user: dict = Depends(get_current_user),
):
    booking = calendar_service.create_booking(
        slot_id=payload.slot_id,
        user_id=current_user["id"],
        notes=payload.notes,
    )
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slot is not available for booking",
        )
    return booking


@router.get("/my-bookings", response_model=list[BookingResponse])
async def list_my_bookings(current_user: dict = Depends(get_current_user)):
    bookings = calendar_service.get_user_bookings(current_user["id"])
    result = []
    for b in bookings:
        slot_data = b.pop("calendar_slots", None)
        b["slot"] = slot_data
        result.append(b)
    return result


@router.get("/bookings/mine", response_model=list[BookingResponse])
async def list_my_bookings_alias(current_user: dict = Depends(get_current_user)):
    """Alias for /my-bookings (used by frontend)."""
    bookings = calendar_service.get_user_bookings(current_user["id"])
    result = []
    for b in bookings:
        slot_data = b.pop("calendar_slots", None)
        b["slot"] = slot_data
        result.append(b)
    return result


@router.delete("/my-bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_my_booking(
    booking_id: str,
    current_user: dict = Depends(get_current_user),
):
    success = calendar_service.cancel_booking(booking_id, user_id=current_user["id"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel this booking",
        )


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


@router.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_booking_by_id(
    booking_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Cancel a booking. Admins can cancel any, users only their own."""
    settings = get_settings()
    is_admin = current_user["username"] == settings.admin_username
    if is_admin:
        success = calendar_service.cancel_booking(booking_id)
    else:
        success = calendar_service.cancel_booking(booking_id, user_id=current_user["id"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel this booking",
        )
