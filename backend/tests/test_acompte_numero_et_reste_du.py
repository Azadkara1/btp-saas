"""
Tests Batch 23 (niveau endpoint, faux client Supabase local — même pattern
que test_documents_transitions.py) :
- POST /documents/{id}/create-acompte pré-remplit numero_document (plus
  besoin de le saisir à la main), best-effort si le profil est introuvable.
- GET /documents calcule montant_restant_du sur un devis signé, à partir
  des factures d'acompte déjà émises pour lui.
"""
import copy

import pytest

from app.models.document import CreateAcompteRequest
from app.routers import documents as documents_router
from app.services import numero_service


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, rows_ref):
        self._rows_ref = rows_ref
        self._eq_filters = []
        self._in_filters = []
        self._is_null_filters = []
        self._update_data = None
        self._insert_data = None

    def select(self, *_a, **_k):
        return self

    def eq(self, field, value):
        self._eq_filters.append((field, value))
        return self

    def in_(self, field, values):
        self._in_filters.append((field, set(values)))
        return self

    def is_(self, field, _value):
        self._is_null_filters.append(field)
        return self

    def order(self, *_a, **_k):
        return self

    def update(self, data):
        self._update_data = data
        return self

    def insert(self, data):
        self._insert_data = data
        return self

    def _matched(self):
        rows = self._rows_ref
        for field, value in self._eq_filters:
            rows = [r for r in rows if r.get(field) == value]
        for field, values in self._in_filters:
            rows = [r for r in rows if r.get(field) in values]
        for field in self._is_null_filters:
            rows = [r for r in rows if r.get(field) is None]
        return rows

    def execute(self):
        if self._insert_data is not None:
            row = dict(self._insert_data)
            row.setdefault("id", "new-id")
            row.setdefault("created_at", "2026-01-01T00:00:00+00:00")
            self._rows_ref.append(row)
            return _FakeResult([row])
        matched = self._matched()
        if self._update_data is not None:
            for r in matched:
                r.update(self._update_data)
        return _FakeResult(copy.deepcopy(matched))


class FakeSupabaseClient:
    def __init__(self, documents=None, entreprises=None):
        self._documents = documents or []
        self._entreprises = entreprises or []

    def table(self, name):
        if name == "documents":
            return _FakeQuery(self._documents)
        if name == "entreprises":
            return _FakeQuery(self._entreprises)
        if name == "clients":
            return _FakeQuery([])
        raise AssertionError(f"table inattendue : {name}")


class _FakeCurrentUser:
    def __init__(self, user_id):
        self.user_id = user_id


def _make_devis_payload(total_ht=1000.0, total_tva=200.0, total_ttc=1200.0):
    return {
        "client": {"nom": "Client Test"},
        "artisan": {"nom": "Artisan Test"},
        "chantier": {"description": "Chantier"},
        "lignes": [{
            "poste": "Travaux", "description": "x", "quantite": 1, "unite": "forfait",
            "prix_unitaire_ht": total_ht, "tva_taux": 20.0, "source_prix": "estimation",
        }],
        "totaux": {"total_ht": total_ht, "total_tva": total_tva, "total_ttc": total_ttc},
        "mentions_legales": [],
    }


def _make_profile_row(**overrides):
    base = dict(
        user_id="user-1",
        compteur_factures=4, compteur_factures_annee=2026,
        facture_numero_debut=1, numero_reset_annuel=True,
        facture_numero_prefixe="FAC-", facture_numero_inclure_annee=True, facture_numero_padding=3,
    )
    base.update(overrides)
    return base


# ── POST /documents/{id}/create-acompte — numéro provisoire auto ───────────

def test_create_acompte_pre_remplit_le_numero_document(monkeypatch):
    doc_row = {
        "id": "devis-1", "user_id": "user-1", "type_doc": "devis", "statut": "signé",
        "titre": "Devis Test", "client_id": None, "numero": "DEV-2026-003",
        "numero_document": "DEV-2026-003", "date_document": "2026-08-25",
        "devis_payload": _make_devis_payload(), "total_ttc": 1200.0,
    }
    fake = FakeSupabaseClient(documents=[doc_row], entreprises=[_make_profile_row()])
    monkeypatch.setattr(documents_router, "get_supabase_admin", lambda: fake)
    monkeypatch.setattr(numero_service, "get_supabase_admin", lambda: fake)

    result = documents_router.create_acompte(
        "devis-1",
        CreateAcompteRequest(mode="pourcentage", pourcentage=30),
        current_user=_FakeCurrentUser("user-1"),
    )

    # compteur_factures_annee == année courante -> prochain compteur = 4+1 = 5
    assert result.numero_document == "FAC-2026-005"


def test_create_acompte_laisse_vide_si_profil_introuvable(monkeypatch):
    """Best-effort : pas de profil entreprises -> pas de crash, numero_document
    reste vide comme avant Batch 23 (l'artisan peut toujours le saisir)."""
    doc_row = {
        "id": "devis-1", "user_id": "user-1", "type_doc": "devis", "statut": "signé",
        "titre": "Devis Test", "client_id": None, "numero": "DEV-2026-003",
        "numero_document": "DEV-2026-003", "date_document": "2026-08-25",
        "devis_payload": _make_devis_payload(), "total_ttc": 1200.0,
    }
    fake = FakeSupabaseClient(documents=[doc_row], entreprises=[])  # pas de profil
    monkeypatch.setattr(documents_router, "get_supabase_admin", lambda: fake)
    monkeypatch.setattr(numero_service, "get_supabase_admin", lambda: fake)

    result = documents_router.create_acompte(
        "devis-1",
        CreateAcompteRequest(mode="montant_fixe", montant_ttc=360.0),
        current_user=_FakeCurrentUser("user-1"),
    )

    assert result.numero_document is None
    assert result.total_ttc == 360.0


# ── GET /documents — montant_restant_du ─────────────────────────────────────

def test_list_documents_calcule_le_reste_du_sur_devis_signe(monkeypatch):
    devis_row = {
        "id": "devis-1", "user_id": "user-1", "type_doc": "devis", "statut": "signé",
        "titre": "Devis Test", "numero": "DEV-2026-003", "numero_document": "DEV-2026-003",
        "client_id": None, "total_ttc": 1200.0, "date_document": "2026-08-25",
        "created_at": "2026-08-25T00:00:00+00:00", "document_source_id": None,
        "date_envoi": None, "date_signature": "2026-08-26T00:00:00+00:00",
        "date_paiement": None, "date_refus": None, "date_expiration": None,
        "date_email_envoye": None, "email_destinataire": None, "signature_nom_signataire": "Client",
    }
    acompte_row = {
        "id": "acompte-1", "user_id": "user-1", "type_doc": "facture", "statut": "envoyé",
        "titre": "Facture d'acompte", "numero": "FAC-2026-001", "numero_document": "FAC-2026-001",
        "client_id": None, "total_ttc": 360.0, "date_document": "2026-08-27",
        "created_at": "2026-08-27T00:00:00+00:00", "document_source_id": "devis-1",
        "devis_payload": {"type_facture": "acompte"},
        "date_envoi": None, "date_signature": None, "date_paiement": None, "date_refus": None,
        "date_expiration": None, "date_email_envoye": None, "email_destinataire": None,
        "signature_nom_signataire": None,
    }
    fake = FakeSupabaseClient(documents=[devis_row, acompte_row])
    monkeypatch.setattr(documents_router, "get_supabase_admin", lambda: fake)

    result = documents_router.list_documents(current_user=_FakeCurrentUser("user-1"))

    devis_summary = next(d for d in result if d.id == "devis-1")
    acompte_summary = next(d for d in result if d.id == "acompte-1")
    assert devis_summary.montant_restant_du == 840.0  # 1200 - 360
    assert acompte_summary.montant_restant_du is None  # uniquement sur le devis signé


def test_list_documents_reste_du_absent_si_devis_non_signe(monkeypatch):
    devis_row = {
        "id": "devis-1", "user_id": "user-1", "type_doc": "devis", "statut": "envoyé",
        "titre": "Devis Test", "numero": "DEV-2026-003", "numero_document": "DEV-2026-003",
        "client_id": None, "total_ttc": 1200.0, "date_document": "2026-08-25",
        "created_at": "2026-08-25T00:00:00+00:00", "document_source_id": None,
        "date_envoi": "2026-08-25T00:00:00+00:00", "date_signature": None,
        "date_paiement": None, "date_refus": None, "date_expiration": None,
        "date_email_envoye": None, "email_destinataire": None, "signature_nom_signataire": None,
    }
    fake = FakeSupabaseClient(documents=[devis_row])
    monkeypatch.setattr(documents_router, "get_supabase_admin", lambda: fake)

    result = documents_router.list_documents(current_user=_FakeCurrentUser("user-1"))

    assert result[0].montant_restant_du is None
