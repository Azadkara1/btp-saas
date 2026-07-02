"""
Dépendance FastAPI d'authentification.
Vérifie les JWT Supabase via JWKS (RS256/ES256) — aucun secret partagé.
"""
from functools import lru_cache
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError
import jwt

from app.core.config import get_settings

bearer = HTTPBearer(auto_error=True)


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    """Singleton — un seul client par processus ; rafraîchit le JWKS toutes les 5 min."""
    return PyJWKClient(
        get_settings().supabase_jwks_url,
        cache_jwk_set=True,
        lifespan=300,
    )


class CurrentUser:
    __slots__ = ("user_id", "email")

    def __init__(self, user_id: str, email: str | None) -> None:
        self.user_id = user_id
        self.email   = email


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> CurrentUser:
    token = credentials.credentials
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
            options={"verify_exp": True},
        )
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return CurrentUser(user_id=payload["sub"], email=payload.get("email"))
