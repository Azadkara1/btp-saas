from pydantic import BaseModel
from typing import Optional


class CaMoisPoint(BaseModel):
    mois: str   # "YYYY-MM"
    ca: float


class TopPrestation(BaseModel):
    poste: str
    ca: float


class DashboardStats(BaseModel):
    """Statistiques agrégées côté SQL (fonction Postgres get_dashboard_stats)."""
    ca_signe: float = 0
    ca_en_attente: float = 0
    ca_encaisse: float = 0
    taux_conversion: float = 0                              # % de devis envoyés → signés
    panier_moyen: float = 0
    delai_moyen_signature_jours: Optional[float] = None      # None = aucune paire envoi/signature
    repartition_statuts: dict[str, int] = {}
    ca_par_mois: list[CaMoisPoint] = []                       # 12 derniers mois, y compris à 0
    top_prestations: list[TopPrestation] = []
