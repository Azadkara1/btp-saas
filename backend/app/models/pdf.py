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
