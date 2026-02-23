from datetime import datetime, timezone
from app.db.connection import get_supabase_client


def create_plan(data: dict) -> dict:
    client = get_supabase_client()
    result = client.table("payment_plans").insert(data).execute()
    return result.data[0]


def update_plan(plan_id: str, data: dict) -> dict | None:
    client = get_supabase_client()
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = (
        client.table("payment_plans")
        .update(data)
        .eq("id", plan_id)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def get_plan_by_id(plan_id: str) -> dict | None:
    client = get_supabase_client()
    result = (
        client.table("payment_plans")
        .select("*")
        .eq("id", plan_id)
        .maybe_single()
        .execute()
    )
    return result.data if result else None


def get_active_plans() -> list[dict]:
    client = get_supabase_client()
    result = (
        client.table("payment_plans")
        .select("*")
        .eq("is_active", True)
        .order("price_cents")
        .execute()
    )
    return result.data


def get_all_plans() -> list[dict]:
    client = get_supabase_client()
    result = (
        client.table("payment_plans")
        .select("*")
        .order("created_at")
        .execute()
    )
    return result.data


def create_payment(user_id: str, data: dict) -> dict:
    client = get_supabase_client()
    data["user_id"] = user_id
    result = client.table("user_payments").insert(data).execute()
    return result.data[0]


def update_payment_status(payment_id: str, data: dict) -> dict | None:
    client = get_supabase_client()
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    if data.get("status") == "cancelled":
        data["cancelled_at"] = datetime.now(timezone.utc).isoformat()
    result = (
        client.table("user_payments")
        .update(data)
        .eq("id", payment_id)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def get_user_subscription(user_id: str) -> dict | None:
    client = get_supabase_client()
    result = (
        client.table("user_payments")
        .select("*, payment_plans(*)")
        .eq("user_id", user_id)
        .in_("status", ["active", "pending"])
        .order("created_at", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    return result.data if result else None


def get_user_payment_history(user_id: str) -> list[dict]:
    client = get_supabase_client()
    result = (
        client.table("user_payments")
        .select("*, payment_plans(*)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


def get_all_payments() -> list[dict]:
    client = get_supabase_client()
    result = (
        client.table("user_payments")
        .select("*, payment_plans(*), users(username, email)")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data
