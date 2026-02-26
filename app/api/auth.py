from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, status
from app.models.user import UserCreate, UserLogin, TokenResponse, UserProfile, PasswordChange
from app.services import user_service, token_blacklist_service
from app.core.security import create_access_token, decode_access_token
from app.core.config import get_settings
from app.core.dependencies import get_current_user, security_scheme
from fastapi.security import HTTPAuthorizationCredentials

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate):
    if user_service.get_user_by_username(payload.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )
    if user_service.get_user_by_email(payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = user_service.create_user(
        username=payload.username,
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone_number=payload.phone_number,
    )
    return user_service.strip_sensitive_fields(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin):
    user = user_service.authenticate_user(payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    settings = get_settings()
    role = "admin" if user["username"] == settings.admin_username else "user"
    token = create_access_token(data={"sub": user["id"], "username": user["username"], "role": role})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserProfile)
async def get_me(current_user: dict = Depends(get_current_user)):
    return user_service.strip_sensitive_fields(current_user)


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
):
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    exp = payload.get("exp")
    if exp:
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc).isoformat()
    else:
        expires_at = datetime.now(timezone.utc).isoformat()

    token_blacklist_service.blacklist_token(token, expires_at)
    return {"message": "Logout effettuato con successo"}


@router.post("/change-password")
async def change_password(
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
