"""
Modèles Pydantic dédiés à la page publique de signature (Batch 12 T3).

⚠️ Projection volontairement restreinte de Devis/ArtisanInfo/ClientInfo —
jamais les champs sensibles (IBAN, BIC, email artisan, user_id). Ne JAMAIS
renvoyer devis_payload brut sur une route publique : c'est exactement le
genre d'endroit où une fuite passe inaperçue.
"""
from pydantic import BaseModel
from typing import Optional, List

from app.models.document import StatutDocument
from app.models.quote import ChantierInfo, LigneDevis, TotauxDevis


class PublicArtisanInfo(BaseModel):
    """Sous-ensemble d'ArtisanInfo sûr à exposer publiquement — jamais iban/bic/email."""
    nom: Optional[str] = None
    siret: Optional[str] = None
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    telephone: Optional[str] = None
    site_web: Optional[str] = None
    logo_base64: Optional[str] = None
    assurance_nom: Optional[str] = None
    assurance_contrat: Optional[str] = None
    assurance_couverture: Optional[str] = None


class PublicClientInfo(BaseModel):
    """Sous-ensemble de ClientInfo — pas d'email non plus, inutile pour l'affichage."""
    nom: Optional[str] = None
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None


class PublicDevisView(BaseModel):
    """Vue en lecture seule d'un devis, exposée sans authentification via /public/devis/{token}."""
    numero_document: Optional[str] = None
    statut: StatutDocument
    date_document: Optional[str] = None
    validite_jours: Optional[int] = None
    conditions_paiement: Optional[str] = None
    modele: Optional[str] = "moderne"
    afficher_signature: bool = True
    client: PublicClientInfo
    artisan: PublicArtisanInfo
    chantier: ChantierInfo
    lignes: List[LigneDevis]
    totaux: TotauxDevis
    mentions_legales: List[str]
    signable: bool                         # True seulement si statut == "envoyé"
    deja_signe_par: Optional[str] = None   # nom du signataire si déjà signé
    deja_signe_le: Optional[str] = None    # date_signature si déjà signé


class AcceptSignatureRequest(BaseModel):
    nom_signataire: str
    signature_image_base64: Optional[str] = None  # dessin à main levée (PNG base64) — optionnel


class PublicActionResponse(BaseModel):
    statut: str
