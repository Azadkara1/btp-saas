"""
Routeur profil entreprise — Lot 2.
GET  /profile  → profil de l'utilisateur connecté (404 si absent)
PUT  /profile  → upsert du profil

⚠️  Client service_role : filtrage user_id obligatoire sur chaque requête.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user, CurrentUser
from app.core.supabase_client import get_supabase_admin
from app.models.profile import ProfileEntreprise

router = APIRouter()

# Champs gérés par ProfileEntreprise (exclut id, user_id, created_at, compteurs)
_PROFILE_FIELDS = set(ProfileEntreprise.model_fields.keys())


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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil introuvable")

    return ProfileEntreprise(**{k: v for k, v in result.data[0].items() if k in _PROFILE_FIELDS})


@router.put("", response_model=ProfileEntreprise)
def put_profile(
    profile: ProfileEntreprise,
    current_user: CurrentUser = Depends(get_current_user),
):
    db = get_supabase_admin()
    try:
        existing = (
            db.table("entreprises")
            .select("id")
            .eq("user_id", current_user.user_id)
            .execute()
        )

        data = profile.model_dump()

        if existing.data:
            db.table("entreprises").update(data).eq("user_id", current_user.user_id).execute()
        else:
            db.table("entreprises").insert({**data, "user_id": current_user.user_id}).execute()

    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    return profile
