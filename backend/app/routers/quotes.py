"""
Router FastAPI pour la génération de devis.
Route principale : POST /quotes/generate
"""
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request
from app.models.quote import QuoteRequest, QuoteResponse
from app.services.claude_service import generate_quote

router = APIRouter(prefix="/quotes", tags=["Devis"])

# ── Rate limiting simple en mémoire ─────────────────────────────
_rate_store: dict[str, list] = defaultdict(list)
_RATE_LIMIT  = 10   # max requêtes par fenêtre
_RATE_WINDOW = 60   # secondes


def _check_rate_limit(client_ip: str) -> bool:
    now    = datetime.utcnow()
    cutoff = now - timedelta(seconds=_RATE_WINDOW)
    _rate_store[client_ip] = [t for t in _rate_store[client_ip] if t > cutoff]
    if len(_rate_store[client_ip]) >= _RATE_LIMIT:
        return False
    _rate_store[client_ip].append(now)
    return True


@router.post("/generate", response_model=QuoteResponse)
async def generate_quote_endpoint(request: QuoteRequest, req: Request):
    """
    Génère un devis professionnel à partir d'une description textuelle.

    - Analyse la description via Claude Sonnet
    - Recherche les prix manquants via Tool Use
    - Retourne un devis JSON structuré et validé
    - Limité à 10 requêtes/minute par IP
    """
    client_ip = req.client.host if req.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Trop de requetes. Reessayez dans une minute."
        )

    if not request.description.strip():
        raise HTTPException(status_code=400, detail="La description du chantier est obligatoire.")

    result = await generate_quote(request)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return result


@router.get("/health")
async def health_check():
    """Vérifie que le service de génération de devis est opérationnel."""
    return {"status": "ok", "service": "quotes"}
