"""
Tests de routers/clients.py — jamais couvert jusqu'ici (trouvé par revue de
code, Batch 16). Filtrage user_id, agrégation nb_documents/CA, 404 croisé
entre utilisateurs.
"""
import copy

import pytest
from fastapi import HTTPException

from app.models.client import ClientUpdate
from app.routers import clients as clients_router


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, rows_ref):
        self._rows_ref = rows_ref
        self._eq_filters = []
        self._is_null_filters = []
        self._update_data = None

    def select(self, *_a, **_k):
        return self

    def eq(self, field, value):
        self._eq_filters.append((field, value))
        return self

    def is_(self, field, _value):
        self._is_null_filters.append(field)
        return self

    def order(self, *_a, **_k):
        return self

    def update(self, data):
        self._update_data = data
        return self

    def _matched(self):
        rows = self._rows_ref
        for field, value in self._eq_filters:
            rows = [r for r in rows if r.get(field) == value]
        for field in self._is_null_filters:
            rows = [r for r in rows if r.get(field) is None]
        return rows

    def execute(self):
        matched = self._matched()
        if self._update_data is not None:
            for r in matched:
                r.update(self._update_data)
        return _FakeResult(copy.deepcopy(matched))


class FakeSupabaseClient:
    def __init__(self, clients=None, documents=None):
        self._clients = clients or []
        self._documents = documents or []

    def table(self, name):
        if name == "clients":
            return _FakeQuery(self._clients)
        if name == "documents":
            return _FakeQuery(self._documents)
        raise AssertionError(f"table inattendue : {name}")


class _FakeCurrentUser:
    def __init__(self, user_id):
        self.user_id = user_id


def _make_client(**overrides):
    base = dict(id="client-1", user_id="user-1", nom="Client Test", adresse=None, code_postal=None, ville=None)
    base.update(overrides)
    return base


def _make_doc(**overrides):
    base = dict(
        id="doc-1", user_id="user-1", client_id="client-1", type_doc="devis",
        titre="Devis", numero=None, numero_document=None, total_ttc=1000.0,
        statut="envoyé", date_document="2026-08-25", created_at="2026-08-25T00:00:00+00:00",
        document_source_id=None, date_envoi=None, date_signature=None, date_paiement=None,
        date_refus=None, date_expiration=None, date_email_envoye=None, email_destinataire=None,
        signature_nom_signataire=None, deleted_at=None,
    )
    base.update(overrides)
    return base


# ── GET /clients — agrégation nb_documents/CA ────────────────────────────────

def test_list_clients_agrege_nb_documents_et_ca_par_client(monkeypatch):
    fake = FakeSupabaseClient(
        clients=[_make_client(id="c1", nom="Alice"), _make_client(id="c2", nom="Bob")],
        documents=[
            _make_doc(client_id="c1", total_ttc=1000.0),
            _make_doc(client_id="c1", total_ttc=500.0),
            _make_doc(client_id="c2", total_ttc=2000.0),
        ],
    )
    monkeypatch.setattr(clients_router, "get_supabase_admin", lambda: fake)

    result = clients_router.list_clients(current_user=_FakeCurrentUser("user-1"))

    by_id = {c.id: c for c in result}
    assert by_id["c1"].nb_documents == 2
    assert by_id["c1"].ca_total == 1500.0
    assert by_id["c2"].nb_documents == 1
    assert by_id["c2"].ca_total == 2000.0


def test_list_clients_ignore_les_documents_dun_autre_utilisateur(monkeypatch):
    """Le filtrage user_id est déjà fait par la requête Supabase (.eq côté
    fake) — ce test vérifie que list_clients ne recompose pas l'agrégation
    à partir de données non filtrées."""
    fake = FakeSupabaseClient(
        clients=[_make_client(id="c1", user_id="user-1")],
        documents=[
            _make_doc(client_id="c1", user_id="user-1", total_ttc=100.0),
            _make_doc(client_id="c1", user_id="user-2", total_ttc=99999.0),  # autre utilisateur
        ],
    )
    monkeypatch.setattr(clients_router, "get_supabase_admin", lambda: fake)

    result = clients_router.list_clients(current_user=_FakeCurrentUser("user-1"))
    assert result[0].ca_total == 100.0


# ── GET /clients/{id} ─────────────────────────────────────────────────────────

def test_get_client_404_si_autre_utilisateur(monkeypatch):
    fake = FakeSupabaseClient(clients=[_make_client(user_id="user-1")])
    monkeypatch.setattr(clients_router, "get_supabase_admin", lambda: fake)

    with pytest.raises(HTTPException) as exc:
        clients_router.get_client("client-1", current_user=_FakeCurrentUser("user-2"))
    assert exc.value.status_code == 404


def test_get_client_retourne_fiche_et_historique(monkeypatch):
    fake = FakeSupabaseClient(
        clients=[_make_client()],
        documents=[_make_doc(total_ttc=750.0)],
    )
    monkeypatch.setattr(clients_router, "get_supabase_admin", lambda: fake)

    result = clients_router.get_client("client-1", current_user=_FakeCurrentUser("user-1"))
    assert result.nom == "Client Test"
    assert result.nb_documents == 1
    assert result.ca_total == 750.0
    assert result.documents[0].id == "doc-1"


# ── PUT /clients/{id} ─────────────────────────────────────────────────────────

def test_update_client_404_si_autre_utilisateur(monkeypatch):
    fake = FakeSupabaseClient(clients=[_make_client(user_id="user-1")])
    monkeypatch.setattr(clients_router, "get_supabase_admin", lambda: fake)

    with pytest.raises(HTTPException) as exc:
        clients_router.update_client(
            "client-1", ClientUpdate(nom="Nouveau nom"), current_user=_FakeCurrentUser("user-2")
        )
    assert exc.value.status_code == 404


def test_update_client_400_si_aucune_donnee(monkeypatch):
    fake = FakeSupabaseClient(clients=[_make_client()])
    monkeypatch.setattr(clients_router, "get_supabase_admin", lambda: fake)

    with pytest.raises(HTTPException) as exc:
        clients_router.update_client("client-1", ClientUpdate(), current_user=_FakeCurrentUser("user-1"))
    assert exc.value.status_code == 400


def test_update_client_persiste_les_nouvelles_coordonnees(monkeypatch):
    client_row = _make_client()
    fake = FakeSupabaseClient(clients=[client_row])
    monkeypatch.setattr(clients_router, "get_supabase_admin", lambda: fake)

    result = clients_router.update_client(
        "client-1", ClientUpdate(ville="Lyon"), current_user=_FakeCurrentUser("user-1")
    )
    assert result.ville == "Lyon"
    assert client_row["ville"] == "Lyon"
