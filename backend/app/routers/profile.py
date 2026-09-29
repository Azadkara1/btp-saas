"""
Routeur profil entreprise — Lot 2.
GET  /profile  → profil de l'utilisateur connecté (404 si absent)
PUT  /profile  → upsert du profil
GET  /profile/numerotation-status → verrouillage + aperçu du prochain numéro
                                     (devis et facture) — Batch 13 T2

⚠️  Client service_role : filtrage user_id obligatoire sur chaque requête.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import get_current_user, CurrentUser
from app.core.supabase_client import get_supabase_admin
from app.models.profile import ProfileEntreprise
from app.services.numero_service import preview_next_compteur

logger = logging.getLogger(__name__)
router = APIRouter()

# Champs gérés par ProfileEntreprise (exclut id, user_id, created_at, compteurs)
_PROFILE_FIELDS = set(ProfileEntreprise.model_fields.keys())

# Batch 13 T2 — le point de départ ne peut plus changer une fois qu'un numéro
# légal a été attribué pour ce type (numérotation chronologique continue).
_NUMERO_DEBUT_LOCK_FIELDS = {
    "devis": "devis_numero_debut",
    "facture": "facture_numero_debut",
}


@router.get("", response_model=ProfileEntreprise)
def get_profile(current_user: CurrentUser = Depends(get_current_user)):
    try:
        result = (
            get_supabase_admin()
            .table("entreprises")
            .select("*")
            .eq("user_id", current_user.user_id)
            .execute()
        )
    except Exception as exc:
        logger.error("Erreur interne inattendue : %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil introuvable")

    return ProfileEntreprise(**{k: v for k, v in result.data[0].items() if k in _PROFILE_FIELDS})


def _numero_debut_locked(db, uid: str, type_doc: str) -> bool:
    """Un numéro légal a-t-il déjà été attribué pour ce type de document ?
    Si oui, le point de départ configuré ne doit plus pouvoir changer —
    vérifié ici (backend), pas seulement dans le formulaire."""
    res = (
        db.table("documents")
        .select("id")
        .eq("user_id", uid)
        .eq("type_doc", type_doc)
        .not_.is_("numero", "null")
        .limit(1)
        .execute()
    )
    return bool(res.data)


@router.put("", response_model=ProfileEntreprise)
def put_profile(
    profile: ProfileEntreprise,
    current_user: CurrentUser = Depends(get_current_user),
):
    db = get_supabase_admin()
    uid = current_user.user_id
    try:
        existing = (
            db.table("entreprises")
            .select("*")
            .eq("user_id", uid)
            .execute()
        )

        # Batch 13 T2 — verrouillage du point de départ (piège #2, côté backend)
        if existing.data:
            existing_row = existing.data[0]
            for type_doc, field in _NUMERO_DEBUT_LOCK_FIELDS.items():
                incoming = getattr(profile, field)
                current_value = existing_row.get(field)
                if current_value is not None and incoming != current_value and _numero_debut_locked(db, uid, type_doc):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Le point de départ de numérotation des {type_doc}s ne peut plus être modifié : "
                            f"un numéro a déjà été attribué. La numérotation légale doit rester continue."
                        ),
                    )

        data = profile.model_dump()

        if existing.data:
            db.table("entreprises").update(data).eq("user_id", uid).execute()
        else:
            db.table("entreprises").insert({**data, "user_id": uid}).execute()

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erreur interne inattendue : %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

    return profile


# ── Batch 13 T2 : statut de verrouillage + aperçu du prochain numéro ────────

class NumerotationStatus(BaseModel):
    devis_locked: bool
    devis_prochain_compteur: int
    facture_locked: bool
    facture_prochain_compteur: int


@router.get("/numerotation-status", response_model=NumerotationStatus)
def get_numerotation_status(current_user: CurrentUser = Depends(get_current_user)):
    """Verrouillage + valeur brute du prochain compteur (devis et facture).
    Le frontend reformate localement (prefixe/année/padding) pour un aperçu
    en direct qui suit la saisie sans round-trip à chaque frappe."""
    db = get_supabase_admin()
    uid = current_user.user_id
    try:
        return NumerotationStatus(
            devis_locked=_numero_debut_locked(db, uid, "devis"),
            devis_prochain_compteur=preview_next_compteur(uid, "devis"),
            facture_locked=_numero_debut_locked(db, uid, "facture"),
            facture_prochain_compteur=preview_next_compteur(uid, "facture"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erreur interne inattendue : %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")
