"""
Modèle Pydantic du profil entreprise (Lot 2).
Distinct d'ArtisanInfo pour ne pas modifier quote.py.
Colonnes miroir de la table `entreprises` (hors id, user_id, created_at, et les
compteurs runtime compteur_devis/compteur_devis_annee/compteur_factures/
compteur_factures_annee — internes à get_next_numero, jamais exposés).
Les champs devis_numero_*/facture_numero_*/numero_reset_annuel sont de la
CONFIGURATION éditable par l'artisan (Batch 13 T2), distincts des compteurs
runtime ci-dessus. `PUT /profile` verrouille devis_numero_debut/facture_numero_debut
dès qu'un numéro légal a déjà été attribué pour ce type (cf. routers/profile.py).
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
    assurance_nom: Optional[str] = None
    assurance_contrat: Optional[str] = None
    assurance_couverture: Optional[str] = None
    modele_prefere: str = "moderne"
    # Numérotation personnalisable par compte (Batch 13 T2) — défauts = comportement
    # historique inchangé (DEV-YYYY-NNN / FAC-YYYY-NNN à partir de 1, reset annuel).
    devis_numero_debut: int = 1
    devis_numero_prefixe: str = "DEV-"
    devis_numero_inclure_annee: bool = True
    devis_numero_padding: int = 3
    facture_numero_debut: int = 1
    facture_numero_prefixe: str = "FAC-"
    facture_numero_inclure_annee: bool = True
    facture_numero_padding: int = 3
    numero_reset_annuel: bool = True
