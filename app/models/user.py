from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Any


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone_number: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class TradeZellaDataUpdate(BaseModel):
    tradezella_data: dict[str, Any]


class UserProfile(BaseModel):
    id: str
    username: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    is_active: bool
    tradezella_data: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class UserListItem(BaseModel):
    id: str
    username: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    is_active: bool
    tradezella_data: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
