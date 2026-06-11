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
    claude_model: str = "claude-sonnet-4-20250514"

    # ── App ─────────────────────────────────────────────────────
    app_name: str = "BTP SaaS"
    debug: bool = False
    frontend_url: str = "http://localhost:3000"

    # ── Étape 2 (à remplir plus tard) ───────────────────────────
    # database_url: str = ""
    # stripe_secret_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Singleton — chargé une seule fois au démarrage."""
    return Settings()
