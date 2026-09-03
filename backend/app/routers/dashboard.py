"""
Routeur dashboard — Phase 5.

GET /dashboard/stats → statistiques agrégées (CA, conversion, panier moyen,
                        répartition statuts, CA par mois, top prestations),
                        calculées côté SQL (fonction Postgres get_dashboard_stats,
                        jamais de boucle Python sur tous les documents).
"""
from fastapi import APIRouter, Depends

from app.core.auth import get_current_user, CurrentUser
from app.models.dashboard import DashboardStats
from app.services.dashboard_service import get_dashboard_stats_raw

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
def get_stats(current_user: CurrentUser = Depends(get_current_user)):
    data = get_dashboard_stats_raw(current_user.user_id)
    return DashboardStats(**data)
