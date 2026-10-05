"""
Tests de routers/evenements.py (Batch 20 — Calendrier partagé).
Isolation par user_id, validation fin >= début, bornes de longueur,
filtrage par plage de dates (chevauchement).
"""
import copy
import uuid
from datetime import datetime

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.evenement import EvenementCreate, EvenementUpdate
from app.routers import evenements as evenements_router


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, rows_ref):
        self._rows_ref = rows_ref
        self._eq_filters = []
        self._lte_filters = []
        self._gte_filters = []
        self._update_data = None
        self._insert_data = None
        self._delete = False

    def select(self, *_a, **_k):
        return self

    def eq(self, field, value):
        self._eq_filters.append((field, value))
        return self

    def lte(self, field, value):
        self._lte_filters.append((field, value))
        return self

    def gte(self, field, value):
        self._gte_filters.append((field, value))
        return self

    def order(self, *_a, **_k):
        return self

    def update(self, data):
        self._update_data = data
        return self

    def insert(self, data):
        self._insert_data = data
        return self

    def delete(self):
        self._delete = True
        return self

    def _matched(self):
        rows = self._rows_ref
        for field, value in self._eq_filters:
            rows = [r for r in rows if r.get(field) == value]
        for field, value in self._lte_filters:
            rows = [r for r in rows if r.get(field) <= value]
        for field, value in self._gte_filters:
            rows = [r for r in rows if r.get(field) >= value]
        return rows

    def execute(self):
        if self._insert_data is not None:
            row = dict(self._insert_data)
            row["id"] = str(uuid.uuid4())
            row.setdefault("description", None)
            row["created_at"] = "2026-10-05T00:00:00+00:00"
            row["updated_at"] = "2026-10-05T00:00:00+00:00"
            self._rows_ref.append(row)
            return _FakeResult([copy.deepcopy(row)])

        matched = self._matched()
        if self._update_data is not None:
            for r in matched:
                r.update(self._update_data)
            return _FakeResult(copy.deepcopy(matched))
        if self._delete:
            for r in matched:
                self._rows_ref.remove(r)
            return _FakeResult(copy.deepcopy(matched))
        return _FakeResult(copy.deepcopy(matched))


class FakeSupabaseClient:
    def __init__(self, evenements=None):
        self._evenements = evenements or []

    def table(self, name):
        if name == "evenements":
            return _FakeQuery(self._evenements)
        raise AssertionError(f"table inattendue : {name}")


class _FakeCurrentUser:
    def __init__(self, user_id):
        self.user_id = user_id


def _make_evenement(**overrides):
    base = dict(
        id="evt-1", user_id="user-1", titre="Chantier Dupont",
        description=None, date_debut="2026-10-05T14:00:00+00:00",
        date_fin="2026-10-05T16:00:00+00:00", toute_la_journee=False,
        cree_par="Karim", created_at="2026-10-05T00:00:00+00:00",
        updated_at="2026-10-05T00:00:00+00:00",
    )
    base.update(overrides)
    return base


# ── Validation Pydantic ───────────────────────────────────────────────────

def test_evenement_create_refuse_fin_avant_debut():
    with pytest.raises(ValidationError):
        EvenementCreate(
            titre="Test", date_debut="2026-10-05T16:00:00Z",
            date_fin="2026-10-05T14:00:00Z", cree_par="Karim",
        )


def test_evenement_create_accepte_fin_egale_debut():
    e = EvenementCreate(
        titre="Test", date_debut="2026-10-05T14:00:00Z",
        date_fin="2026-10-05T14:00:00Z", cree_par="Karim",
    )
    assert e.titre == "Test"


def test_evenement_create_refuse_titre_vide():
    with pytest.raises(ValidationError):
        EvenementCreate(
            titre="", date_debut="2026-10-05T14:00:00Z",
            date_fin="2026-10-05T16:00:00Z", cree_par="Karim",
        )


def test_evenement_create_refuse_titre_trop_long():
    with pytest.raises(ValidationError):
        EvenementCreate(
            titre="x" * 121, date_debut="2026-10-05T14:00:00Z",
            date_fin="2026-10-05T16:00:00Z", cree_par="Karim",
        )


def test_evenement_update_refuse_fin_avant_debut_si_les_deux_fournis():
    with pytest.raises(ValidationError):
        EvenementUpdate(date_debut="2026-10-05T16:00:00Z", date_fin="2026-10-05T14:00:00Z")


def test_evenement_update_accepte_un_seul_champ_date():
    u = EvenementUpdate(date_debut="2026-10-05T16:00:00Z")
    assert u.date_debut == "2026-10-05T16:00:00Z"


# ── GET /evenements — isolation user_id + chevauchement de plage ─────────────

def test_list_evenements_isole_par_user_id(monkeypatch):
    fake = FakeSupabaseClient(evenements=[
        _make_evenement(id="e1", user_id="user-1"),
        _make_evenement(id="e2", user_id="user-2"),
    ])
    monkeypatch.setattr(evenements_router, "get_supabase_admin", lambda: fake)

    result = evenements_router.list_evenements(
        debut=datetime.fromisoformat("2026-10-01T00:00:00+00:00"),
        fin=datetime.fromisoformat("2026-10-31T23:59:59+00:00"),
        current_user=_FakeCurrentUser("user-1"),
    )
    assert [e.id for e in result] == ["e1"]


def test_list_evenements_filtre_par_chevauchement_de_plage(monkeypatch):
    fake = FakeSupabaseClient(evenements=[
        _make_evenement(id="dans", date_debut="2026-10-05T14:00:00+00:00", date_fin="2026-10-05T16:00:00+00:00"),
        _make_evenement(id="avant", date_debut="2026-09-01T14:00:00+00:00", date_fin="2026-09-01T16:00:00+00:00"),
        _make_evenement(id="apres", date_debut="2026-11-01T14:00:00+00:00", date_fin="2026-11-01T16:00:00+00:00"),
    ])
    monkeypatch.setattr(evenements_router, "get_supabase_admin", lambda: fake)

    result = evenements_router.list_evenements(
        debut=datetime.fromisoformat("2026-10-01T00:00:00+00:00"),
        fin=datetime.fromisoformat("2026-10-31T23:59:59+00:00"),
        current_user=_FakeCurrentUser("user-1"),
    )
    assert [e.id for e in result] == ["dans"]


# ── POST /evenements ──────────────────────────────────────────────────────────

def test_create_evenement_attribue_user_id_courant(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(evenements_router, "get_supabase_admin", lambda: fake)

    body = EvenementCreate(
        titre="Nouveau chantier", date_debut="2026-10-05T14:00:00Z",
        date_fin="2026-10-05T16:00:00Z", cree_par="Karim",
    )
    result = evenements_router.create_evenement(body, current_user=_FakeCurrentUser("user-1"))

    assert result.titre == "Nouveau chantier"
    assert fake._evenements[0]["user_id"] == "user-1"


# ── PUT /evenements/{id} ──────────────────────────────────────────────────────

def test_update_evenement_404_si_autre_utilisateur(monkeypatch):
    fake = FakeSupabaseClient(evenements=[_make_evenement(user_id="user-1")])
    monkeypatch.setattr(evenements_router, "get_supabase_admin", lambda: fake)

    with pytest.raises(HTTPException) as exc:
        evenements_router.update_evenement(
            "evt-1", EvenementUpdate(titre="Modifié"), current_user=_FakeCurrentUser("user-2")
        )
    assert exc.value.status_code == 404


def test_update_evenement_400_si_aucune_donnee(monkeypatch):
    fake = FakeSupabaseClient(evenements=[_make_evenement()])
    monkeypatch.setattr(evenements_router, "get_supabase_admin", lambda: fake)

    with pytest.raises(HTTPException) as exc:
        evenements_router.update_evenement("evt-1", EvenementUpdate(), current_user=_FakeCurrentUser("user-1"))
    assert exc.value.status_code == 400


def test_update_evenement_400_si_nouvelle_date_fin_avant_date_debut_existante(monkeypatch):
    """date_debut existant = 14h, on essaie de ne changer que date_fin à 10h → incohérent."""
    fake = FakeSupabaseClient(evenements=[_make_evenement(
        date_debut="2026-10-05T14:00:00+00:00", date_fin="2026-10-05T16:00:00+00:00"
    )])
    monkeypatch.setattr(evenements_router, "get_supabase_admin", lambda: fake)

    with pytest.raises(HTTPException) as exc:
        evenements_router.update_evenement(
            "evt-1", EvenementUpdate(date_fin="2026-10-05T10:00:00+00:00"),
            current_user=_FakeCurrentUser("user-1"),
        )
    assert exc.value.status_code == 400


def test_update_evenement_persiste_le_nouveau_titre(monkeypatch):
    row = _make_evenement()
    fake = FakeSupabaseClient(evenements=[row])
    monkeypatch.setattr(evenements_router, "get_supabase_admin", lambda: fake)

    result = evenements_router.update_evenement(
        "evt-1", EvenementUpdate(titre="Chantier reporté"), current_user=_FakeCurrentUser("user-1")
    )
    assert result.titre == "Chantier reporté"
    assert row["titre"] == "Chantier reporté"


# ── DELETE /evenements/{id} ───────────────────────────────────────────────────

def test_delete_evenement_404_si_autre_utilisateur(monkeypatch):
    fake = FakeSupabaseClient(evenements=[_make_evenement(user_id="user-1")])
    monkeypatch.setattr(evenements_router, "get_supabase_admin", lambda: fake)

    with pytest.raises(HTTPException) as exc:
        evenements_router.delete_evenement("evt-1", current_user=_FakeCurrentUser("user-2"))
    assert exc.value.status_code == 404


def test_delete_evenement_supprime_physiquement(monkeypatch):
    fake = FakeSupabaseClient(evenements=[_make_evenement()])
    monkeypatch.setattr(evenements_router, "get_supabase_admin", lambda: fake)

    evenements_router.delete_evenement("evt-1", current_user=_FakeCurrentUser("user-1"))
    assert fake._evenements == []
