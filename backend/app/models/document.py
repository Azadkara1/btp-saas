from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional

# Statuts possibles d'un document — cf. contrainte documents_statut_check (avec accents)
StatutDocument = Literal["brouillon", "envoyé", "signé", "payé", "refusé", "expiré"]


class DocumentCreate(BaseModel):
    type_doc: str
    titre: Optional[str] = None
    numero_document: Optional[str] = None
    date_document: Optional[str] = None
    devis_payload: dict
    total_ttc: Optional[float] = None
    client_nom: Optional[str] = None
    client_adresse: Optional[str] = None
    client_code_postal: Optional[str] = None
    client_ville: Optional[str] = None


class DocumentSummary(BaseModel):
    id: str
    type_doc: str
    titre: Optional[str] = None
    numero: Optional[str] = None
    numero_document: Optional[str] = None
    client_nom: Optional[str] = None
    total_ttc: Optional[float] = None
    statut: str
    date_document: Optional[str] = None
    created_at: str
    document_source_id: Optional[str] = None
    date_envoi: Optional[str] = None
    date_signature: Optional[str] = None
    date_paiement: Optional[str] = None
    date_refus: Optional[str] = None
    date_expiration: Optional[str] = None
    date_email_envoye: Optional[str] = None
    email_destinataire: Optional[str] = None
    signature_nom_signataire: Optional[str] = None


class DocumentDetail(DocumentSummary):
    devis_payload: dict
    # Uniquement dans Detail (jamais dans la liste Summary) : peut peser
    # plusieurs dizaines de Ko, inutile de l'envoyer pour chaque ligne d'historique.
    signature_image_base64: Optional[str] = None


class StatusUpdate(BaseModel):
    statut: StatutDocument


class StatusPatchResponse(BaseModel):
    statut: str
    numero: Optional[str] = None


class SendEmailRequest(BaseModel):
    email_destinataire: EmailStr
    message: Optional[str] = None


class SendEmailResponse(BaseModel):
    statut: str
    numero: Optional[str] = None
    date_email_envoye: str


class CreateAcompteRequest(BaseModel):
    pourcentage: float = Field(..., gt=0, le=100, description="Pourcentage du total HT du devis (ex: 30)")
