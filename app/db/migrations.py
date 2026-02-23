from passlib.context import CryptContext
from app.db.connection import get_supabase_client
from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def run_admin_upsert():
    settings = get_settings()
    client = get_supabase_client()

    password_hash = pwd_context.hash(settings.admin_password)

    existing = (
        client.table("users")
        .select("id")
        .eq("username", settings.admin_username)
        .maybe_single()
        .execute()
    )

    if existing.data:
        client.table("users").update({
            "username": settings.admin_username,
            "email": settings.admin_email,
            "password_hash": password_hash,
        }).eq("id", existing.data["id"]).execute()
    else:
        client.table("users").insert({
            "username": settings.admin_username,
            "email": settings.admin_email,
            "password_hash": password_hash,
            "first_name": None,
            "last_name": None,
            "phone_number": None,
            "is_active": True,
            "tradezella_data": None,
        }).execute()
