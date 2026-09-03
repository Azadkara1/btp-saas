from fastapi import HTTPException, status

from app.core.supabase_client import get_supabase_admin


def get_dashboard_stats_raw(user_id: str) -> dict:
    """
    Appelle la RPC Postgres get_dashboard_stats — agrégation SQL pure
    (CA, conversion, panier moyen, répartition statuts, CA/mois, top prestations).
    Retourne le dict JSON brut, prêt à passer à DashboardStats(**data).
    """
    try:
        result = (
            get_supabase_admin()
            .rpc("get_dashboard_stats", {"p_user_id": user_id})
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur agrégation dashboard : {exc}",
        )

    data = result.data
    # supabase-py peut retourner le scalaire jsonb directement (dict) ou enveloppé
    # dans une liste selon la version de PostgREST — on normalise ici (cf. numero_service.py).
    if isinstance(data, list):
        data = data[0] if data else {}
        if isinstance(data, dict) and "get_dashboard_stats" in data and len(data) == 1:
            data = data["get_dashboard_stats"]

    if not isinstance(data, dict):
        data = {}

    return data
