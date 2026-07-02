from pydantic import BaseModel
from typing import Optional


class DocumentCreate(BaseModel):
    type_doc: str  # "devis" | "facture"
    date_document: Optional[str] = None  # ISO date "YYYY-MM-DD"
    devis_payload: dict  # Devis complet sérialisé
    total_ttc: Optional[float] = None
    client_nom: Optional[str] = None
    client_adresse: Optional[str] = None
    client_code_postal: Optional[str] = None
    client_ville: Optional[str] = None


class DocumentSummary(BaseModel):
    id: str
    type_doc: str
    numero: Optional[str] = None
    client_nom: Optional[str] = None
    total_ttc: Optional[float] = None
    statut: str
    date_document: Optional[str] = None
    created_at: str


class DocumentDetail(DocumentSummary):
    devis_payload: dict


class StatusUpdate(BaseModel):
    statut: str


class StatusPatchResponse(BaseModel):
    statut: str
    numero: Optional[str] = None
