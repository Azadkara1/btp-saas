"""
Schémas Pydantic pour la génération PDF.
"""
from typing import Optional
from pydantic import BaseModel
from .quote import Devis


class PdfRequest(BaseModel):
    """Requête de génération PDF — contient le devis complet."""
    devis: Devis
    template: str = "default"               # Prévu pour plusieurs templates à l'Étape 2
    document_type: str = "devis"            # "devis" ou "facture"
    with_tva: bool = True                   # False → masque TVA + mention art. 293 B
    document_date: Optional[str] = None    # Format ISO "YYYY-MM-DD", None = aujourd'hui
    # Signature capturée (Batch 12 T3) — métadonnée du document, pas du devis
    # lui-même, donc hors de Devis/quote.py. Fournie par le frontend quand un
    # document déjà signé électroniquement est réexporté.
    signature_nom_signataire: Optional[str] = None
    signature_image_base64: Optional[str] = None
    signature_date: Optional[str] = None
