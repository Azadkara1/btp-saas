"""
Modèle Pydantic du profil entreprise (Lot 2).
Distinct d'ArtisanInfo pour ne pas modifier quote.py.
Colonnes miroir de la table `entreprises` (hors id, user_id, created_at, compteurs).
"""
from pydantic import BaseModel
from typing import Optional


class ProfileEntreprise(BaseModel):
    nom: Optional[str] = None
    siret: Optional[str] = None
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    site_web: Optional[str] = None
    logo_base64: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    modele_prefere: str = "moderne"
