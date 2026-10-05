from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from typing import Optional


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class EvenementCreate(BaseModel):
    titre: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=1000)
    date_debut: str
    date_fin: str
    toute_la_journee: bool = False
    cree_par: str = Field(..., min_length=1, max_length=80)

    @model_validator(mode="after")
    def _check_dates(self) -> "EvenementCreate":
        try:
            debut, fin = _parse_iso(self.date_debut), _parse_iso(self.date_fin)
        except ValueError:
            raise ValueError("date_debut/date_fin doivent être des dates ISO 8601 valides")
        if fin < debut:
            raise ValueError("date_fin doit être postérieure ou égale à date_debut")
        return self


class EvenementUpdate(BaseModel):
    titre: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=1000)
    date_debut: Optional[str] = None
    date_fin: Optional[str] = None
    toute_la_journee: Optional[bool] = None
    cree_par: Optional[str] = Field(None, min_length=1, max_length=80)

    @model_validator(mode="after")
    def _check_dates(self) -> "EvenementUpdate":
        # Validation complète (y compris si un seul des deux champs change)
        # faite dans le routeur, qui fusionne avec le document existant —
        # ici on ne peut vérifier que le cas où les DEUX sont fournis ensemble.
        if self.date_debut is not None and self.date_fin is not None:
            try:
                debut, fin = _parse_iso(self.date_debut), _parse_iso(self.date_fin)
            except ValueError:
                raise ValueError("date_debut/date_fin doivent être des dates ISO 8601 valides")
            if fin < debut:
                raise ValueError("date_fin doit être postérieure ou égale à date_debut")
        return self


class Evenement(BaseModel):
    id: str
    titre: str
    description: Optional[str] = None
    date_debut: str
    date_fin: str
    toute_la_journee: bool
    cree_par: str
    created_at: str
    updated_at: str
