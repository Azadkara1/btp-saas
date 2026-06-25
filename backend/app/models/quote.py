"""
Schémas Pydantic pour les devis.
Source de vérité pour la validation entrée/sortie de l'API.
Ces modèles seront réutilisés à l'Étape 2 pour la persistance BDD.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class SourcePrix(str, Enum):
    ARTISAN = "artisan"
    RECHERCHE_MARCHE = "recherche_marche"
    ESTIMATION = "estimation"


class LigneDevis(BaseModel):
    lot: Optional[str] = Field(None, description="Groupe LOT (ex: LOT 1 — Peinture)")
    poste: str = Field(..., description="Nom du poste (ex: Maçonnerie, Main d'œuvre)")
    description: str = Field(..., description="Détail de la prestation")
    quantite: Optional[float] = Field(None, ge=0)  # None = "au réel" (traité comme ×1 dans tous les calculs)
    unite: str = Field(..., description="Unité (m², ml, forfait, heure...)")
    prix_unitaire_ht: float = Field(..., ge=0)
    tva_taux: float = Field(..., description="Taux TVA en % (ex: 10.0, 20.0, 5.5)")
    source_prix: SourcePrix = SourcePrix.ESTIMATION

    @property
    def montant_ht(self) -> float:
        qty = self.quantite if self.quantite is not None else 1.0
        return round(qty * self.prix_unitaire_ht, 2)

    @property
    def montant_tva(self) -> float:
        return round(self.montant_ht * self.tva_taux / 100, 2)

    @property
    def montant_ttc(self) -> float:
        return round(self.montant_ht + self.montant_tva, 2)


class ClientInfo(BaseModel):
    nom: Optional[str] = None
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None


class ArtisanInfo(BaseModel):
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


class ChantierInfo(BaseModel):
    description: str
    adresse: Optional[str] = None


class TotauxDevis(BaseModel):
    total_ht: float
    total_tva: float
    total_ttc: float
    remise_ht: float = 0.0
    total_ht_net: float = 0.0
    net_a_payer: float = 0.0


class Devis(BaseModel):
    """Modèle complet d'un devis généré par l'IA."""
    client: ClientInfo = ClientInfo()
    artisan: ArtisanInfo = ArtisanInfo()
    chantier: ChantierInfo
    lignes: List[LigneDevis]
    totaux: TotauxDevis
    mentions_legales: List[str] = [
        "TVA applicable selon taux en vigueur"
    ]
    notes: Optional[str] = None
    numero_document: Optional[str] = None
    remise_type: Optional[str] = None      # "pourcentage" | "montant_fixe"
    remise_valeur: Optional[float] = None
    acompte: Optional[float] = None
    modele: Optional[str] = "moderne"     # "moderne" | "pro" — injecté post-génération, jamais envoyé à Claude
    validite_jours: Optional[int] = None  # durée de validité devis (jours) — libre, rien si absent
    conditions_paiement: Optional[str] = None  # ex: "30% à la commande, solde à réception"


# ── Prix personnalisés fournis par l'artisan ─────────────────────
class PrixArtisan(BaseModel):
    """Un tarif saisi manuellement par l'artisan pour une prestation."""
    prestation: str = Field(..., description="Nom de la prestation (ex: Pose carrelage)")
    prix_unitaire_ht: float = Field(..., ge=0, description="Prix unitaire HT en euros")
    unite: str = Field(default="", description="Unité (m², heure, unité…)")


# ── Requête entrante ─────────────────────────────────────────────
class QuoteRequest(BaseModel):
    """Ce que le frontend envoie au backend."""
    description: str = Field(
        ...,
        min_length=10,
        description="Description libre du chantier par l'artisan"
    )
    region: str = Field(
        default="Île-de-France",
        description="Région pour la recherche des prix du marché"
    )
    artisan_nom: Optional[str] = None
    artisan_siret: Optional[str] = None
    artisan_iban: Optional[str] = None
    artisan_bic: Optional[str] = None
    artisan_adresse: Optional[str] = None
    artisan_code_postal: Optional[str] = None
    artisan_ville: Optional[str] = None
    artisan_telephone: Optional[str] = None
    artisan_email: Optional[str] = None
    artisan_site_web: Optional[str] = None
    artisan_logo_base64: Optional[str] = None
    client_nom: Optional[str] = None
    client_adresse: Optional[str] = None
    client_code_postal: Optional[str] = None
    client_ville: Optional[str] = None
    numero_document: Optional[str] = None
    remise_type: Optional[str] = None
    remise_valeur: Optional[float] = None
    acompte: Optional[float] = None
    modele: Optional[str] = "moderne"
    validite_jours: Optional[int] = None
    conditions_paiement: Optional[str] = None
    prix_personnalises: Optional[List[PrixArtisan]] = Field(
        default=None,
        description="Tarifs de l'artisan à utiliser en priorité"
    )


# ── Réponse sortante ─────────────────────────────────────────────
class QuoteResponse(BaseModel):
    """Ce que le backend retourne au frontend."""
    success: bool
    devis: Optional[Devis] = None
    error: Optional[str] = None
    tokens_used: Optional[int] = None
    import_meta: Optional[dict] = None  # Uniquement renseigné par l'import (jamais par la génération)
