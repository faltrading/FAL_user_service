from pydantic import BaseModel
from datetime import datetime
from typing import Any


class PaymentPlanCreate(BaseModel):
    name: str
    description: str | None = None
    price_cents: int
    currency: str = "EUR"
    billing_interval: str = "monthly"
    features: dict[str, Any] | None = None
    is_active: bool = True


class PaymentPlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price_cents: int | None = None
    currency: str | None = None
    billing_interval: str | None = None
    features: dict[str, Any] | None = None
    is_active: bool | None = None


class PaymentPlanResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    price_cents: int
    currency: str
    billing_interval: str
    features: dict[str, Any] | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserPaymentCreate(BaseModel):
    plan_id: str | None = None
    status: str = "pending"
    payment_provider: str | None = None
    external_payment_id: str | None = None
    amount_cents: int | None = None
    currency: str = "EUR"
    started_at: datetime | None = None
    expires_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class PaymentStatusUpdate(BaseModel):
    status: str
    external_payment_id: str | None = None
    metadata: dict[str, Any] | None = None


class UserPaymentResponse(BaseModel):
    id: str
    user_id: str
    plan_id: str | None = None
    status: str
    payment_provider: str | None = None
    external_payment_id: str | None = None
    amount_cents: int | None = None
    currency: str
    started_at: datetime | None = None
    expires_at: datetime | None = None
    cancelled_at: datetime | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
