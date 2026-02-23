from fastapi import APIRouter, HTTPException, Depends, status
from app.models.user import (
    UserUpdate,
    PasswordChange,
    UserProfile,
    UserListItem,
    TradeZellaDataUpdate,
)
from app.services import user_service
from app.core.dependencies import get_current_user, get_current_admin

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me/profile", response_model=UserProfile)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    return user_service.strip_sensitive_fields(current_user)


@router.put("/me", response_model=UserProfile)
async def update_my_profile(
    payload: UserUpdate,
    current_user: dict = Depends(get_current_user),
):
    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    if "email" in update_data and update_data["email"] != current_user["email"]:
        existing = user_service.get_user_by_email(update_data["email"])
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

    updated = user_service.update_user(current_user["id"], update_data)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )
    return user_service.strip_sensitive_fields(updated)


@router.put("/me/password")
async def change_my_password(
    payload: PasswordChange,
    current_user: dict = Depends(get_current_user),
):
    success = user_service.change_password(
        current_user["id"], payload.current_password, payload.new_password
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    return {"message": "Password updated successfully"}


@router.get("/", response_model=list[UserListItem])
async def list_all_users(admin: dict = Depends(get_current_admin)):
    users = user_service.get_all_users()
    return [user_service.strip_sensitive_fields(u) for u in users]


@router.get("/{user_id}", response_model=UserProfile)
async def get_user_profile(user_id: str, admin: dict = Depends(get_current_admin)):
    user = user_service.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user_service.strip_sensitive_fields(user)


@router.put("/{user_id}/tradezella-data", response_model=UserProfile)
async def update_tradezella_data(
    user_id: str,
    payload: TradeZellaDataUpdate,
    admin: dict = Depends(get_current_admin),
):
    user = user_service.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    updated = user_service.update_tradezella_data(user_id, payload.tradezella_data)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update TradeZella data",
        )
    return user_service.strip_sensitive_fields(updated)
