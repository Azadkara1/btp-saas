"""
Router FastAPI pour la génération et l'import de devis.
Routes :
  POST /quotes/generate  — génération IA depuis description texte
  POST /quotes/import    — extraction depuis un PDF ou .docx existant
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from app.models.quote import QuoteRequest, QuoteResponse
from app.services.claude_service import generate_quote
from app.services.import_service import import_quote

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


@router.post("/import", response_model=QuoteResponse)
async def import_quote_endpoint(
    req: Request,
    file: UploadFile = File(..., description="Fichier PDF ou .docx à importer"),
    artisan_nom:         Optional[str] = Form(None),
    artisan_siret:       Optional[str] = Form(None),
    artisan_iban:        Optional[str] = Form(None),
    artisan_bic:         Optional[str] = Form(None),
    artisan_adresse:     Optional[str] = Form(None),
    artisan_code_postal: Optional[str] = Form(None),
    artisan_ville:       Optional[str] = Form(None),
    artisan_telephone:   Optional[str] = Form(None),
    artisan_email:       Optional[str] = Form(None),
    artisan_site_web:    Optional[str] = Form(None),
    artisan_logo_base64: Optional[str] = Form(None),
    modele:              Optional[str] = Form("moderne"),
):
    """
    Importe un devis ou une facture existant (PDF ou .docx).

    - PDF : envoyé en bloc document à Claude (lecture native, pas de parseur lourd)
    - .docx : texte extrait via python-docx puis envoyé à Claude
    - Les infos artisan du document importé sont ignorées au profit du profil enregistré
    - Retourne un devis JSON éditable dans QuotePreview
    """
    client_ip = req.client.host if req.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Trop de requetes. Reessayez dans une minute.")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni.")

    content = await file.read()

    # Construit le QuoteRequest avec les champs artisan disponibles
    quote_request = QuoteRequest(
        description="import (document importé)",  # champ requis (min 10 chars), non utilisé pour l'import
        artisan_nom=artisan_nom or None,
        artisan_siret=artisan_siret or None,
        artisan_iban=artisan_iban or None,
        artisan_bic=artisan_bic or None,
        artisan_adresse=artisan_adresse or None,
        artisan_code_postal=artisan_code_postal or None,
        artisan_ville=artisan_ville or None,
        artisan_telephone=artisan_telephone or None,
        artisan_email=artisan_email or None,
        artisan_site_web=artisan_site_web or None,
        artisan_logo_base64=artisan_logo_base64 or None,
        modele=modele or "moderne",
    )

    result = await import_quote(content, file.filename, quote_request)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return result


@router.get("/health")
async def health_check():
    """Vérifie que le service de génération de devis est opérationnel."""
    return {"status": "ok", "service": "quotes"}
