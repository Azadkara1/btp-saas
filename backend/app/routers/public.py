"""
Routeur public — signature électronique du devis par le client (Batch 12 T3).

⚠️ AUCUNE authentification sur ce routeur — accessible par quiconque possède
le token (256 bits d'aléatoire, cf. `secrets.token_urlsafe(32)` dans
routers/documents.py::get_signature_link). Ne JAMAIS ajouter
Depends(get_current_user) ici — ce serait contradictoire avec le principe
même de la page publique. Ne JAMAIS renvoyer un champ hors du modèle
PublicDevisView (jamais devis_payload brut, jamais user_id).

GET  /public/devis/{token}          → vue en lecture seule
POST /public/devis/{token}/accept   → signature (statut → signé)
POST /public/devis/{token}/refuse   → refus (statut → refusé)
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status

from app.core.supabase_client import get_supabase_admin
from app.models.public import (
    AcceptSignatureRequest,
    PublicActionResponse,
    PublicArtisanInfo,
    PublicClientInfo,
    PublicDevisView,
)
from app.models.quote import Devis
from app.routers.documents import _statut_transition_update
from app.services.email_service import send_devis_email
from app.services.pdf_service import generate_quote_pdf

logger = logging.getLogger(__name__)
router = APIRouter()

_STATUTS_NON_SIGNABLES_MESSAGE = {
    "brouillon": "Ce devis n'a pas encore été envoyé par l'artisan.",
    "signé": "Ce devis a déjà été signé.",
    "refusé": "Ce devis a été refusé.",
    "payé": "Ce document a déjà été traité.",
    "expiré": "Ce devis a expiré. Contactez votre artisan pour un nouveau devis.",
}


def _is_signable(statut: str) -> bool:
    return statut == "envoyé"


def _fetch_by_token(token: str) -> dict:
    """Résout un token en document. 404 si absent/invalide, 410 si expiré."""
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lien invalide")

    db = get_supabase_admin()
    res = (
        db.table("documents")
        .select("*")
        .eq("signature_token", token)
        .eq("type_doc", "devis")
        .is_("deleted_at", "null")
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lien invalide")

    doc = res.data[0]

    expires_raw = doc.get("signature_token_expires_at")
    if expires_raw:
        expires_at = datetime.fromisoformat(str(expires_raw).replace("Z", "+00:00"))
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Ce lien de signature a expiré.")

    return doc


@router.get("/devis/{token}", response_model=PublicDevisView)
def get_public_devis(token: str):
    doc = _fetch_by_token(token)
    devis = Devis(**doc["devis_payload"])

    return PublicDevisView(
        numero_document=devis.numero_document,
        statut=doc["statut"],
        date_document=str(doc["date_document"]) if doc.get("date_document") else None,
        validite_jours=devis.validite_jours,
        conditions_paiement=devis.conditions_paiement,
        modele=devis.modele,
        afficher_signature=devis.afficher_signature,
        client=PublicClientInfo(
            nom=devis.client.nom,
            adresse=devis.client.adresse,
            code_postal=devis.client.code_postal,
            ville=devis.client.ville,
        ),
        artisan=PublicArtisanInfo(
            nom=devis.artisan.nom,
            siret=devis.artisan.siret,
            adresse=devis.artisan.adresse,
            code_postal=devis.artisan.code_postal,
            ville=devis.artisan.ville,
            telephone=devis.artisan.telephone,
            site_web=devis.artisan.site_web,
            logo_base64=devis.artisan.logo_base64,
            assurance_nom=devis.artisan.assurance_nom,
            assurance_contrat=devis.artisan.assurance_contrat,
            assurance_couverture=devis.artisan.assurance_couverture,
            statut_juridique=devis.artisan.statut_juridique,
            forme_juridique=devis.artisan.forme_juridique,
            capital_social=devis.artisan.capital_social,
        ),
        chantier=devis.chantier,
        lignes=devis.lignes,
        totaux=devis.totaux,
        mentions_legales=devis.mentions_legales,
        signable=_is_signable(doc["statut"]),
        deja_signe_par=doc.get("signature_nom_signataire"),
        deja_signe_le=str(doc["date_signature"]) if doc.get("date_signature") else None,
    )


@router.post("/devis/{token}/accept", response_model=PublicActionResponse)
def accept_devis(token: str, body: AcceptSignatureRequest, request: Request):
    doc = _fetch_by_token(token)

    if not _is_signable(doc["statut"]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_STATUTS_NON_SIGNABLES_MESSAGE.get(doc["statut"], "Ce devis ne peut plus être signé."),
        )

    nom = body.nom_signataire.strip()
    if not nom:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le nom du signataire est requis.")

    signature_image = body.signature_image_base64
    if signature_image:
        if signature_image.startswith("data:"):
            signature_image = signature_image.split(",", 1)[-1]
        # Garde-fou taille : route non authentifiée, pas de raison d'accepter un
        # payload énorme pour un simple dessin de signature (~2 Mo décodés max).
        if len(signature_image) > 2_800_000:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image de signature trop volumineuse.")

    db = get_supabase_admin()
    update_data = _statut_transition_update(doc["user_id"], doc, "signé")
    update_data["signature_nom_signataire"] = nom
    update_data["signature_image_base64"] = signature_image
    update_data["signature_ip"] = request.client.host if request.client else None
    update_data["signature_user_agent"] = request.headers.get("user-agent")

    try:
        db.table("documents").update(update_data).eq("id", doc["id"]).execute()
    except Exception as exc:
        logger.error("Erreur interne inattendue : %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

    logger.info("[SIGNATURE] devis %s signé par %r", doc["id"], nom)

    # Batch 14 : notifie l'artisan par email avec le PDF signé en pièce jointe.
    # Best-effort — le client a déjà la confirmation que sa signature est
    # enregistrée (statut mis à jour ci-dessus) ; un échec d'email (Resend
    # non configuré, domaine non vérifié...) ne doit jamais invalider ça.
    _notifier_artisan_signature(doc, update_data)

    return PublicActionResponse(statut="signé")


def _notifier_artisan_signature(doc: dict, update_data: dict) -> None:
    try:
        devis = Devis(**doc["devis_payload"])
        artisan_email = devis.artisan.email
        if not artisan_email:
            logger.info("[SIGNATURE] pas d'email artisan renseigné, notification ignorée (devis %s)", doc["id"])
            return

        with_tva = devis.totaux.total_tva > 0
        pdf_bytes = generate_quote_pdf(
            devis, "devis", with_tva, doc.get("date_document"),
            signature_nom_signataire=update_data.get("signature_nom_signataire"),
            signature_image_base64=update_data.get("signature_image_base64"),
            signature_date=update_data.get("date_signature"),
        )

        numero = devis.numero_document or doc.get("numero") or "sans-numero"
        numero_safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in numero)
        nom_signataire = update_data.get("signature_nom_signataire", "")

        send_devis_email(
            to=artisan_email,
            subject=f"Devis {numero} signé par {nom_signataire}",
            html_body=(
                f"<p>Bonne nouvelle : votre devis <strong>{numero}</strong> vient d'être signé "
                f"électroniquement par <strong>{nom_signataire}</strong>.</p>"
                f"<p>Vous trouverez le document signé en pièce jointe.</p>"
            ),
            pdf_bytes=pdf_bytes,
            pdf_filename=f"devis_signe_{numero_safe}.pdf",
        )
    except Exception as exc:
        logger.warning("[SIGNATURE] échec notification email artisan (devis %s) : %s", doc["id"], exc)


@router.post("/devis/{token}/refuse", response_model=PublicActionResponse)
def refuse_devis(token: str):
    doc = _fetch_by_token(token)

    if not _is_signable(doc["statut"]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_STATUTS_NON_SIGNABLES_MESSAGE.get(doc["statut"], "Ce devis ne peut plus être refusé."),
        )

    db = get_supabase_admin()
    update_data = _statut_transition_update(doc["user_id"], doc, "refusé")

    try:
        db.table("documents").update(update_data).eq("id", doc["id"]).execute()
    except Exception as exc:
        logger.error("Erreur interne inattendue : %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

    logger.info("[SIGNATURE] devis %s refusé", doc["id"])
    return PublicActionResponse(statut="refusé")
