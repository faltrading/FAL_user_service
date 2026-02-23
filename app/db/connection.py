from supabase import create_client, Client
from app.core.config import get_settings

_client: Client | None = None


def get_supabase_client() -> Client:
    global _client
    if _client is None:
        settings = get_settings()
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _client


def execute_sql(query: str, params: list | None = None) -> dict:
    client = get_supabase_client()
    if params:
        result = client.rpc("exec_sql", {"query": query, "params": params}).execute()
    else:
        result = client.postgrest.rpc("exec_sql", {"query": query}).execute()
    return result.data
