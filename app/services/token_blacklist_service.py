import hashlib
import logging

from app.db.connection import get_supabase_client

logger = logging.getLogger(__name__)

# In-memory cache: once a token is confirmed blacklisted, skip future DB lookups
_blacklisted_cache: set[str] = set()


def _hash_token(token: str) -> str:
    """SHA-256 hash of the raw JWT for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def blacklist_token(token: str, expires_at_iso: str) -> None:
    """Add a token to the blacklist."""
    token_hash = _hash_token(token)
    client = get_supabase_client()
    try:
        client.table("token_blacklist").upsert(
            {"token_hash": token_hash, "expires_at": expires_at_iso},
            on_conflict="token_hash",
        ).execute()
        _blacklisted_cache.add(token_hash)
    except Exception as e:
        logger.error(f"Failed to blacklist token: {e}")
        raise


def is_token_blacklisted(token: str) -> bool:
    """Check whether a token has been revoked."""
    token_hash = _hash_token(token)

    # Fast path: already confirmed blacklisted in this process
    if token_hash in _blacklisted_cache:
        return True

    client = get_supabase_client()
    result = (
        client.table("token_blacklist")
        .select("id")
        .eq("token_hash", token_hash)
        .maybe_single()
        .execute()
    )
    if result.data is not None:
        _blacklisted_cache.add(token_hash)
        return True
    return False


def cleanup_expired_tokens() -> int:
    """Remove expired tokens from the blacklist (housekeeping)."""
    from datetime import datetime, timezone

    client = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()
    result = (
        client.table("token_blacklist")
        .delete()
        .lt("expires_at", now)
        .execute()
    )
    removed = len(result.data) if result.data else 0
    if removed:
        logger.info(f"Cleaned up {removed} expired blacklisted tokens")
    return removed
