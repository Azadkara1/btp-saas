"""
Client Supabase service_role pour les appels backend (Lot 2+).
Singleton via lru_cache — instancié une seule fois au démarrage.

⚠️  Ce client bypasse la RLS.
    Chaque requête DOIT filtrer manuellement sur user_id = current_user.user_id.
"""
from functools import lru_cache
from supabase import create_client, Client
from app.core.config import get_settings


@lru_cache()
def get_supabase_admin() -> Client:
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_service_role_key)
