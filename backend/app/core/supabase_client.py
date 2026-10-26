"""
Client Supabase service_role pour les appels backend (Lot 2+).
Singleton via lru_cache — instancié une seule fois au démarrage.

⚠️  Ce client bypasse la RLS.
    Chaque requête DOIT filtrer manuellement sur user_id = current_user.user_id.
"""
from functools import lru_cache

import httpx
from supabase import create_client, Client
from supabase.client import ClientOptions
from app.core.config import get_settings


@lru_cache()
def get_supabase_admin() -> Client:
    s = get_settings()
    # Batch 24 : ce client est un singleton pour toute la durée de vie du
    # process (uvicorn/Render) — httpx garde ses connexions HTTP/2 ouvertes
    # en pool. S'il ne se passe rien pendant un moment, Supabase (ou un proxy
    # intermédiaire) ferme la connexion silencieusement côté serveur ; au
    # prochain appel, httpx tente de la réutiliser et échoue avec
    # "httpcore.RemoteProtocolError: Server disconnected" -> 500 intermittent,
    # jamais reproductible à la demande (observé sur GET /documents).
    # keepalive_expiry court = on abandonne une connexion avant qu'elle ait
    # une chance de devenir stale côté serveur ; retries=1 en filet de
    # sécurité pour le cas où ça arrive quand même.
    httpx_client = httpx.Client(
        timeout=120,
        limits=httpx.Limits(max_keepalive_connections=10, keepalive_expiry=5.0),
        transport=httpx.HTTPTransport(retries=1),
    )
    return create_client(
        s.supabase_url,
        s.supabase_service_role_key,
        options=ClientOptions(httpx_client=httpx_client),
    )
