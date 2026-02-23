from fastapi import APIRouter, HTTPException, Depends, status
from app.models.payment import (
    PaymentPlanCreate,
    PaymentPlanUpdate,
    PaymentPlanResponse,
    UserPaymentCreate,
    UserPaymentResponse,
    PaymentStatusUpdate,
)
from app.services import payment_service
from app.core.dependencies import get_current_user, get_current_admin

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("/plans", response_model=list[PaymentPlanResponse])
async def list_active_plans(current_user: dict = Depends(get_current_user)):
    return payment_service.get_active_plans()


@router.post("/plans", response_model=PaymentPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    payload: PaymentPlanCreate,
    admin: dict = Depends(get_current_admin),
):
    data = payload.model_dump(mode="json")
    return payment_service.create_plan(data)


@router.put("/plans/{plan_id}", response_model=PaymentPlanResponse)
async def update_plan(
    plan_id: str,
    payload: PaymentPlanUpdate,
    admin: dict = Depends(get_current_admin),
):
    existing = payment_service.get_plan_by_id(plan_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment plan not found",
        )

    update_data = payload.model_dump(exclude_none=True, mode="json")
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    result = payment_service.update_plan(plan_id, update_data)
    return result


@router.get("/my-subscription", response_model=UserPaymentResponse | None)
async def get_my_subscription(current_user: dict = Depends(get_current_user)):
    return payment_service.get_user_subscription(current_user["id"])


@router.get("/my-history", response_model=list[UserPaymentResponse])
async def get_my_payment_history(current_user: dict = Depends(get_current_user)):
    return payment_service.get_user_payment_history(current_user["id"])


@router.post("/", response_model=UserPaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: UserPaymentCreate,
    current_user: dict = Depends(get_current_user),
):
    data = payload.model_dump(exclude_none=True, mode="json")
    if "started_at" in data and data["started_at"]:
        data["started_at"] = data["started_at"].isoformat() if not isinstance(data["started_at"], str) else data["started_at"]
    if "expires_at" in data and data["expires_at"]:
        data["expires_at"] = data["expires_at"].isoformat() if not isinstance(data["expires_at"], str) else data["expires_at"]
    return payment_service.create_payment(current_user["id"], data)


@router.put("/{payment_id}/status", response_model=UserPaymentResponse)
async def update_payment_status(
    payment_id: str,
    payload: PaymentStatusUpdate,
    admin: dict = Depends(get_current_admin),
):
    data = payload.model_dump(exclude_none=True, mode="json")
    result = payment_service.update_payment_status(payment_id, data)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    return result


@router.get("/", response_model=list[dict])
async def list_all_payments(admin: dict = Depends(get_current_admin)):
    return payment_service.get_all_payments()
