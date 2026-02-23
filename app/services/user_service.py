from datetime import datetime, timezone
from app.db.connection import get_supabase_client
from app.core.security import hash_password, verify_password


def get_user_by_username(username: str) -> dict | None:
    client = get_supabase_client()
    result = (
        client.table("users")
        .select("*")
        .eq("username", username)
        .maybe_single()
        .execute()
    )
    return result.data if result else None


def get_user_by_email(email: str) -> dict | None:
    client = get_supabase_client()
    result = (
        client.table("users")
        .select("*")
        .eq("email", email)
        .maybe_single()
        .execute()
    )
    return result.data if result else None


def get_user_by_id(user_id: str) -> dict | None:
    client = get_supabase_client()
    result = (
        client.table("users")
        .select("*")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    return result.data if result else None


def create_user(
    username: str,
    email: str,
    password: str,
    first_name: str | None = None,
    last_name: str | None = None,
    phone_number: str | None = None,
) -> dict:
    client = get_supabase_client()
    result = (
        client.table("users")
        .insert({
            "username": username,
            "email": email,
            "password_hash": hash_password(password),
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": phone_number,
        })
        .execute()
    )
    return result.data[0]


def authenticate_user(username: str, password: str) -> dict | None:
    user = get_user_by_username(username)
    if user is None:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    if not user["is_active"]:
        return None
    return user


def update_user(user_id: str, update_data: dict) -> dict | None:
    client = get_supabase_client()
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = (
        client.table("users")
        .update(update_data)
        .eq("id", user_id)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def change_password(user_id: str, current_password: str, new_password: str) -> bool:
    user = get_user_by_id(user_id)
    if user is None:
        return False
    if not verify_password(current_password, user["password_hash"]):
        return False
    update_user(user_id, {"password_hash": hash_password(new_password)})
    return True


def update_tradezella_data(user_id: str, tradezella_data: dict) -> dict | None:
    return update_user(user_id, {"tradezella_data": tradezella_data})


def get_all_users() -> list[dict]:
    client = get_supabase_client()
    result = client.table("users").select("*").order("created_at").execute()
    return result.data


def strip_sensitive_fields(user: dict) -> dict:
    return {k: v for k, v in user.items() if k != "password_hash"}
