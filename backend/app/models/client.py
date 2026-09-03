from pydantic import BaseModel
from typing import Optional

from app.models.document import DocumentSummary


class ClientSummary(BaseModel):
    id: str
    nom: str
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    nb_documents: int = 0
    ca_total: float = 0.0


class ClientDetail(ClientSummary):
    documents: list[DocumentSummary] = []


class ClientUpdate(BaseModel):
    nom: Optional[str] = None
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
