from pydantic import BaseModel
from typing import Any


class AccountDeleteRequest(BaseModel):
    """The user must confirm with their current password."""
    password: str


class AccountDeletionResponse(BaseModel):
    message: str
    user_id: str
    deleted_at: str
    actions: list[str]


class DataExportResponse(BaseModel):
    export_date: str
    user_id: str
    profile: dict[str, Any] | None = None
    bookings: list[dict[str, Any]] = []
    payments: list[dict[str, Any]] = []
    chat_memberships: list[dict[str, Any]] = []
    chat_messages: list[dict[str, Any]] = []
    call_participations: list[dict[str, Any]] = []
    calls_created: list[dict[str, Any]] = []
    broker_connections: list[dict[str, Any]] = []
    broker_trades: list[dict[str, Any]] = []
    broker_daily_stats: list[dict[str, Any]] = []
