"""
Routeur evenements — Batch 20 (Calendrier partagé au sein d'un compte).

GET    /evenements?debut=...&fin=... → événements chevauchant la plage [debut, fin]
POST   /evenements                   → création
PUT    /evenements/{id}              → édition (partielle)
DELETE /evenements/{id}              → suppression physique (pas de donnée légale à tracer)

⚠️ Client service_role : filtrage user_id obligatoire sur chaque requête.
⚠️ Pas de RLS sur la table evenements (cohérent avec documents/clients) —
   la sécurité repose entièrement sur ce filtrage, jamais sur des policies Postgres.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import get_current_user, CurrentUser
from app.core.supabase_client import get_supabase_admin
from app.models.evenement import Evenement, EvenementCreate, EvenementUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


def _row_to_evenement(row: dict) -> Evenement:
    return Evenement(
        id=row["id"],
        titre=row["titre"],
        description=row.get("description"),
        date_debut=row["date_debut"],
        date_fin=row["date_fin"],
        toute_la_journee=row["toute_la_journee"],
        cree_par=row["cree_par"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# ── GET /evenements ──────────────────────────────────────────────────────────

@router.get("", response_model=list[Evenement])
def list_evenements(
    debut: datetime = Query(..., description="Début de la plage (ISO 8601)"),
    fin: datetime = Query(..., description="Fin de la plage (ISO 8601)"),
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = current_user.user_id
    db = get_supabase_admin()

    try:
        res = (
            db.table("evenements")
            .select("*")
            .eq("user_id", uid)
            # Chevauchement de [date_debut, date_fin] avec [debut, fin] :
            # l'événement commence avant la fin de la plage ET finit après son début.
            .lte("date_debut", fin.isoformat())
            .gte("date_fin", debut.isoformat())
            .order("date_debut")
            .execute()
        )
    except Exception as exc:
        logger.error("Erreur interne inattendue : %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

    return [_row_to_evenement(r) for r in (res.data or [])]


# ── POST /evenements ─────────────────────────────────────────────────────────

@router.post("", response_model=Evenement, status_code=status.HTTP_201_CREATED)
def create_evenement(
    body: EvenementCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = current_user.user_id
    db = get_supabase_admin()

    try:
        res = db.table("evenements").insert({
            "user_id": uid,
            "titre": body.titre,
            "description": body.description,
            "date_debut": body.date_debut,
            "date_fin": body.date_fin,
            "toute_la_journee": body.toute_la_journee,
            "cree_par": body.cree_par,
        }).execute()
    except Exception as exc:
        logger.error("Erreur interne inattendue : %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

    return _row_to_evenement(res.data[0])


# ── PUT /evenements/{id} ─────────────────────────────────────────────────────

@router.put("/{evenement_id}", response_model=Evenement)
def update_evenement(
    evenement_id: str,
    body: EvenementUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = current_user.user_id
    db = get_supabase_admin()

    try:
        existing = (
            db.table("evenements")
            .select("*")
            .eq("id", evenement_id)
            .eq("user_id", uid)
            .execute()
        )
    except Exception as exc:
        logger.error("Erreur interne inattendue : %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

    if not existing.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Événement introuvable")

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aucune donnée à mettre à jour")

    # Validation fin >= début sur l'état RÉSULTANT (champ existant + modification
    # partielle) — EvenementUpdate ne peut vérifier ça que si les deux champs
    # sont fournis dans la même requête.
    current = existing.data[0]
    nouveau_debut = update_data.get("date_debut", current["date_debut"])
    nouveau_fin = update_data.get("date_fin", current["date_fin"])
    if datetime.fromisoformat(str(nouveau_fin).replace("Z", "+00:00")) < datetime.fromisoformat(str(nouveau_debut).replace("Z", "+00:00")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="date_fin doit être postérieure ou égale à date_debut")

    update_data["updated_at"] = datetime.utcnow().isoformat()

    try:
        db.table("evenements").update(update_data).eq("id", evenement_id).eq("user_id", uid).execute()
        res = (
            db.table("evenements")
            .select("*")
            .eq("id", evenement_id)
            .eq("user_id", uid)
            .execute()
        )
    except Exception as exc:
        logger.error("Erreur interne inattendue : %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

    return _row_to_evenement(res.data[0])


# ── DELETE /evenements/{id} ──────────────────────────────────────────────────

@router.delete("/{evenement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evenement(
    evenement_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = current_user.user_id
    db = get_supabase_admin()

    try:
        existing = (
            db.table("evenements")
            .select("id")
            .eq("id", evenement_id)
            .eq("user_id", uid)
            .execute()
        )
    except Exception as exc:
        logger.error("Erreur interne inattendue : %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

    if not existing.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Événement introuvable")

    try:
        db.table("evenements").delete().eq("id", evenement_id).eq("user_id", uid).execute()
    except Exception as exc:
        logger.error("Erreur interne inattendue : %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")
