from fastapi import APIRouter, HTTPException, Depends, status
from app.models.user import (
    UserUpdate,
    PasswordChange,
    UserProfile,
    UserListItem,
    TradeZellaDataUpdate,
)
from app.models.gdpr import AccountDeleteRequest, AccountDeletionResponse, DataExportResponse
from app.services import user_service, gdpr_service
from app.core.security import verify_password
from app.core.config import get_settings
from app.core.dependencies import get_current_user, get_current_admin

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserProfile)
async def get_me(current_user: dict = Depends(get_current_user)):
    return user_service.strip_sensitive_fields(current_user)


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


@router.delete("/me", response_model=AccountDeletionResponse)
async def delete_my_account(
    payload: AccountDeleteRequest,
    current_user: dict = Depends(get_current_user),
):
    """GDPR Art. 17 — Right to Erasure. Irreversible."""
    # Prevent admin from deleting their own account
    settings = get_settings()
    if current_user["username"] == settings.admin_username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="L'account admin non può essere eliminato",
        )

    # Verify password
    if not verify_password(payload.password, current_user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password non corretta",
        )

    report = gdpr_service.delete_account(current_user["id"])
    return AccountDeletionResponse(
        message="Account eliminato con successo. Tutti i dati personali sono stati rimossi o anonimizzati.",
        user_id=report["user_id"],
        deleted_at=report["deleted_at"],
        actions=report["actions"],
    )


@router.get("/me/data-export", response_model=DataExportResponse)
async def export_my_data(
    current_user: dict = Depends(get_current_user),
):
    """GDPR Art. 15/20 — Right of Access / Data Portability."""
    return gdpr_service.export_user_data(current_user["id"])


@router.get("/gdpr/export", response_model=DataExportResponse)
async def export_my_data_alias(
    current_user: dict = Depends(get_current_user),
):
    """Alias for /me/data-export (used by frontend)."""
    return gdpr_service.export_user_data(current_user["id"])


@router.post("/gdpr/delete", response_model=AccountDeletionResponse)
async def delete_my_account_alias(
    payload: AccountDeleteRequest,
    current_user: dict = Depends(get_current_user),
):
    """Alias for DELETE /me (used by frontend)."""
    settings = get_settings()
    if current_user["username"] == settings.admin_username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="L'account admin non può essere eliminato",
        )
    if not verify_password(payload.password, current_user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password non corretta",
        )
    report = gdpr_service.delete_account(current_user["id"])
    return AccountDeletionResponse(
        message="Account eliminato con successo. Tutti i dati personali sono stati rimossi o anonimizzati.",
        user_id=report["user_id"],
        deleted_at=report["deleted_at"],
        actions=report["actions"],
    )


@router.get("/search")
async def search_users(
    q: str = "",
    current_user: dict = Depends(get_current_user),
):
    if len(q) < 2:
        return []
    results = user_service.search_users_by_username(q, limit=10)
    return [{"id": u["id"], "username": u["username"]} for u in results]


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
