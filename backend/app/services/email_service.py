"""
Envoi d'email transactionnel via Resend (Batch 11 T4).
Appel REST direct (httpx, déjà une dépendance du projet) plutôt qu'un SDK
dédié — l'API Resend est un simple POST JSON, pas besoin de dépendance
supplémentaire pour ça.

⚠️ RESEND_API_KEY est une clé secrète : jamais côté frontend, jamais en dur
dans le code, définie uniquement via variable d'environnement (.env local,
dashboard Render en production) — même règle que ANTHROPIC_API_KEY.
"""
import base64
import logging

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def send_devis_email(
    to: str,
    subject: str,
    html_body: str,
    pdf_bytes: bytes,
    pdf_filename: str,
) -> None:
    """
    Envoie le PDF du devis/facture en pièce jointe via Resend.
    Lève HTTPException en cas d'échec (clé absente, réseau, refus de Resend) —
    le document ne doit PAS être marqué "envoyé" si cette fonction échoue.
    """
    settings = get_settings()

    if not settings.resend_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Envoi d'email non configuré (RESEND_API_KEY manquante côté serveur).",
        )

    payload = {
        "from": settings.resend_from_email,
        "to": [to],
        "subject": subject,
        "html": html_body,
        "attachments": [
            {
                "filename": pdf_filename,
                "content": base64.b64encode(pdf_bytes).decode("ascii"),
            }
        ],
    }

    try:
        response = httpx.post(
            RESEND_API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            timeout=20.0,
        )
    except httpx.RequestError as exc:
        logger.error("[EMAIL] échec réseau Resend : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Impossible de joindre le service d'envoi d'email : {exc}",
        )

    if response.status_code >= 400:
        logger.error("[EMAIL] Resend a refusé l'envoi (%s) : %s", response.status_code, response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Échec de l'envoi de l'email (Resend {response.status_code}) : {response.text}",
        )

    logger.info("[EMAIL] envoyé à %s — sujet=%r", to, subject)
