"""
Configuration centrale de l'application.
Utilise pydantic-settings pour charger les variables d'environnement.
Prêt pour l'Étape 2 (BDD, Auth) sans modification.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── IA ──────────────────────────────────────────────────────
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-6"

    # ── App ─────────────────────────────────────────────────────
    app_name: str = "BTP SaaS"
    debug: bool = False
    frontend_url: str = "http://localhost:3000"
    allowed_origin: str = "http://localhost:3000"  # CORS — override via ALLOWED_ORIGIN env var

    # ── Supabase — Étape 2 ──────────────────────────────────────
    supabase_url: str = ""  # ex: https://ojuphphxvjpvvtsbbzpq.supabase.co
    supabase_service_role_key: str  # Lot 2 — jamais côté frontend, jamais dans git

    @property
    def supabase_jwks_url(self) -> str:
        """URL du endpoint JWKS Supabase, dérivée de supabase_url."""
        return f"{self.supabase_url}/auth/v1/.well-known/jwks.json"

    # ── Stripe (Lot 4) ───────────────────────────────────────────
    # stripe_secret_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Singleton — chargé une seule fois au démarrage."""
    return Settings()
