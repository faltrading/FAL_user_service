import logging
from datetime import datetime, timezone

from app.db.connection import get_supabase_client

logger = logging.getLogger(__name__)

DELETED_USERNAME = "[utente eliminato]"
DELETED_MESSAGE = "[messaggio eliminato]"


def delete_account(user_id: str) -> dict:
    """
    GDPR Art. 17 — Right to Erasure.

    Anonymises / removes every piece of personal data linked to *user_id*
    across **all** micro-services that share this Supabase project.

    Returns a human-readable report of what was done.
    """
    client = get_supabase_client()
    now_iso = datetime.now(timezone.utc).isoformat()
    report: dict = {
        "user_id": user_id,
        "deleted_at": now_iso,
        "actions": [],
    }

    # ── Chat service ────────────────────────────────────────────────
    # 1. Anonymise messages sent by the user
    try:
        result = (
            client.table("messages")
            .update({
                "sender_username": DELETED_USERNAME,
                "sender_id": None,
                "content": DELETED_MESSAGE,
                "updated_at": now_iso,
            })
            .eq("sender_id", user_id)
            .execute()
        )
        n = len(result.data) if result.data else 0
        report["actions"].append(f"messages_anonymised: {n}")
    except Exception as e:
        logger.warning("Failed to anonymise messages: %s", e)
        report["actions"].append(f"messages_anonymised: error – {e}")

    # 2. Delete read-receipt records
    try:
        result = (
            client.table("message_read_status")
            .delete()
            .eq("user_id", user_id)
            .execute()
        )
        n = len(result.data) if result.data else 0
        report["actions"].append(f"message_read_statuses_deleted: {n}")
    except Exception as e:
        logger.warning("Failed to delete read statuses: %s", e)
        report["actions"].append(f"message_read_statuses_deleted: error – {e}")

    # 3. Remove group memberships
    try:
        result = (
            client.table("group_members")
            .delete()
            .eq("user_id", user_id)
            .execute()
        )
        n = len(result.data) if result.data else 0
        report["actions"].append(f"group_memberships_deleted: {n}")
    except Exception as e:
        logger.warning("Failed to delete group memberships: %s", e)
        report["actions"].append(f"group_memberships_deleted: error – {e}")

    # ── Call service ────────────────────────────────────────────────
    # 4. Anonymise call participation records
    try:
        result = (
            client.table("call_participants")
            .update({"username": DELETED_USERNAME})
            .eq("user_id", user_id)
            .execute()
        )
        n = len(result.data) if result.data else 0
        report["actions"].append(f"call_participants_anonymised: {n}")
    except Exception as e:
        logger.warning("Failed to anonymise call participants: %s", e)
        report["actions"].append(f"call_participants_anonymised: error – {e}")

    # 5. Anonymise calls the user created
    try:
        result = (
            client.table("calls")
            .update({"creator_username": DELETED_USERNAME})
            .eq("created_by", user_id)
            .execute()
        )
        n = len(result.data) if result.data else 0
        report["actions"].append(f"calls_creator_anonymised: {n}")
    except Exception as e:
        logger.warning("Failed to anonymise calls: %s", e)
        report["actions"].append(f"calls_creator_anonymised: error – {e}")

    # ── Broker service ──────────────────────────────────────────────
    # 6. Delete broker connections — CASCADE removes trades, daily_stats, sync_logs
    try:
        result = (
            client.table("broker_connections")
            .delete()
            .eq("user_id", user_id)
            .execute()
        )
        n = len(result.data) if result.data else 0
        report["actions"].append(
            f"broker_connections_deleted: {n} (cascade → trades, daily_stats, sync_logs)"
        )
    except Exception as e:
        logger.warning("Failed to delete broker connections: %s", e)
        report["actions"].append(f"broker_connections_deleted: error – {e}")

    # ── User service (local tables) ────────────────────────────────
    # 7. Delete bookings (FK → users)
    try:
        result = (
            client.table("bookings")
            .delete()
            .eq("user_id", user_id)
            .execute()
        )
        n = len(result.data) if result.data else 0
        report["actions"].append(f"bookings_deleted: {n}")
    except Exception as e:
        logger.warning("Failed to delete bookings: %s", e)
        report["actions"].append(f"bookings_deleted: error – {e}")

    # 8. Delete payment history (FK → users)
    try:
        result = (
            client.table("user_payments")
            .delete()
            .eq("user_id", user_id)
            .execute()
        )
        n = len(result.data) if result.data else 0
        report["actions"].append(f"user_payments_deleted: {n}")
    except Exception as e:
        logger.warning("Failed to delete payments: %s", e)
        report["actions"].append(f"user_payments_deleted: error – {e}")

    # 9. Nullify calendar_slots.created_by (FK → users, nullable)
    try:
        result = (
            client.table("calendar_slots")
            .update({"created_by": None})
            .eq("created_by", user_id)
            .execute()
        )
        n = len(result.data) if result.data else 0
        report["actions"].append(f"calendar_slots_unlinked: {n}")
    except Exception as e:
        logger.warning("Failed to unlink calendar slots: %s", e)
        report["actions"].append(f"calendar_slots_unlinked: error – {e}")

    # 10. Anonymise the user record (keep row for referential integrity)
    try:
        anon_tag = f"deleted_{user_id[:8]}"
        client.table("users").update({
            "username": anon_tag,
            "email": f"{anon_tag}@deleted.local",
            "password_hash": "",
            "first_name": None,
            "last_name": None,
            "phone_number": None,
            "tradezella_data": None,
            "is_active": False,
            "updated_at": now_iso,
        }).eq("id", user_id).execute()
        report["actions"].append("user_record_anonymised")
    except Exception as e:
        logger.warning("Failed to anonymise user record: %s", e)
        report["actions"].append(f"user_record_anonymised: error – {e}")

    logger.info("Account deletion completed for user %s – %s", user_id, report["actions"])
    return report


# ────────────────────────────────────────────────────────────────────
# GDPR Art. 15 / 20 — Right of Access / Data Portability
# ────────────────────────────────────────────────────────────────────

def export_user_data(user_id: str) -> dict:
    """
    Collects and returns every piece of personal data held for *user_id*
    across all micro-services that share this Supabase project.
    """
    client = get_supabase_client()
    export: dict = {
        "export_date": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
    }

    # 1. User profile
    try:
        result = (
            client.table("users")
            .select("*")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        if result.data:
            profile = {k: v for k, v in result.data.items() if k != "password_hash"}
            export["profile"] = profile
        else:
            export["profile"] = None
    except Exception as e:
        logger.warning("Export – user profile: %s", e)
        export["profile"] = {"error": str(e)}

    # 2. Bookings
    try:
        result = (
            client.table("bookings")
            .select("*, calendar_slots(*)")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        export["bookings"] = result.data or []
    except Exception as e:
        logger.warning("Export – bookings: %s", e)
        export["bookings"] = []

    # 3. Payment history
    try:
        result = (
            client.table("user_payments")
            .select("*, payment_plans(*)")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        export["payments"] = result.data or []
    except Exception as e:
        logger.warning("Export – payments: %s", e)
        export["payments"] = []

    # 4. Chat group memberships
    try:
        result = (
            client.table("group_members")
            .select("*, chat_groups(id, name, description)")
            .eq("user_id", user_id)
            .execute()
        )
        export["chat_memberships"] = result.data or []
    except Exception as e:
        logger.warning("Export – chat memberships: %s", e)
        export["chat_memberships"] = []

    # 5. Chat messages
    try:
        result = (
            client.table("messages")
            .select("*")
            .eq("sender_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        export["chat_messages"] = result.data or []
    except Exception as e:
        logger.warning("Export – messages: %s", e)
        export["chat_messages"] = []

    # 6. Call participations
    try:
        result = (
            client.table("call_participants")
            .select("*, calls(id, room_name, created_at)")
            .eq("user_id", user_id)
            .execute()
        )
        export["call_participations"] = result.data or []
    except Exception as e:
        logger.warning("Export – call participations: %s", e)
        export["call_participations"] = []

    # 7. Calls created by the user
    try:
        result = (
            client.table("calls")
            .select("*")
            .eq("created_by", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        export["calls_created"] = result.data or []
    except Exception as e:
        logger.warning("Export – calls created: %s", e)
        export["calls_created"] = []

    # 8. Broker connections (strip encrypted credentials)
    try:
        result = (
            client.table("broker_connections")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        connections = result.data or []
        for conn in connections:
            conn.pop("credentials_encrypted", None)
        export["broker_connections"] = connections
    except Exception as e:
        logger.warning("Export – broker connections: %s", e)
        export["broker_connections"] = []

    # 9. Broker trades
    try:
        result = (
            client.table("broker_trades")
            .select("*")
            .eq("user_id", user_id)
            .order("open_time", desc=True)
            .execute()
        )
        export["broker_trades"] = result.data or []
    except Exception as e:
        logger.warning("Export – broker trades: %s", e)
        export["broker_trades"] = []

    # 10. Broker daily stats
    try:
        result = (
            client.table("broker_daily_stats")
            .select("*")
            .eq("user_id", user_id)
            .order("date", desc=True)
            .execute()
        )
        export["broker_daily_stats"] = result.data or []
    except Exception as e:
        logger.warning("Export – broker daily stats: %s", e)
        export["broker_daily_stats"] = []

    return export
