"""
Tests de la numérotation personnalisable par compte (Batch 13 T2).

`format_numero` / `compute_next_compteur` sont des fonctions pures — testées
directement, sans base de données. Le verrouillage backend (`_numero_debut_locked`,
`put_profile`) est testé via un faux client Supabase en mémoire, même pattern
que `test_public_signature.py`.
"""
import copy

import pytest
from fastapi import HTTPException

from app.services.numero_service import compute_next_compteur, format_numero, preview_next_compteur
from app.routers import profile as profile_router
from app.models.profile import ProfileEntreprise


# ── format_numero — formatage pur ────────────────────────────────────────────

def test_format_numero_defaut_inchange():
    """Non-régression : le format historique DEV-YYYY-NNN ne change pas."""
    assert format_numero(1, "DEV-", True, 3, 2026) == "DEV-2026-001"
    assert format_numero(42, "FAC-", True, 3, 2026) == "FAC-2026-042"


def test_format_numero_point_de_depart_personnalise():
    assert format_numero(2001, "FAC-", True, 4, 2026) == "FAC-2026-2001"


def test_format_numero_prefixe_vide():
    assert format_numero(5, "", True, 3, 2026) == "2026-005"


def test_format_numero_sans_annee():
    assert format_numero(5, "DEV-", False, 3, 2026) == "DEV-005"


def test_format_numero_padding_different():
    assert format_numero(1, "DEV-", True, 5, 2026) == "DEV-2026-00001"
    assert format_numero(123456, "DEV-", True, 3, 2026) == "DEV-2026-123456"  # jamais tronqué


# ── compute_next_compteur — logique de reset ─────────────────────────────────

def test_compute_next_compteur_premier_appel_jamais_fait():
    assert compute_next_compteur(None, None, numero_debut=1, reset_annuel=True, annee_courante=2026) == 1
    assert compute_next_compteur(None, None, numero_debut=2001, reset_annuel=True, annee_courante=2026) == 2001


def test_compute_next_compteur_meme_annee_incremente():
    assert compute_next_compteur(41, 2026, numero_debut=1, reset_annuel=True, annee_courante=2026) == 42


def test_compute_next_compteur_reset_annuel_actif_change_annee():
    assert compute_next_compteur(99, 2025, numero_debut=1, reset_annuel=True, annee_courante=2026) == 1
    assert compute_next_compteur(99, 2025, numero_debut=2001, reset_annuel=True, annee_courante=2026) == 2001


def test_compute_next_compteur_reset_annuel_inactif_continue_malgre_changement_annee():
    assert compute_next_compteur(99, 2025, numero_debut=1, reset_annuel=False, annee_courante=2026) == 100


# ── Compteurs devis / facture indépendants ───────────────────────────────────

class _FakeQuery:
    def __init__(self, rows_ref):
        self._rows_ref = rows_ref
        self._eq_filters = []
        self._not_is_null_filters = []
        self._update_data = None
        self._insert_data = None
        self._limit = None

    def select(self, *_a, **_k):
        return self

    def eq(self, field, value):
        self._eq_filters.append((field, value))
        return self

    def limit(self, n):
        self._limit = n
        return self

    @property
    def not_(self):
        return _NotFilter(self)

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
        for field in self._not_is_null_filters:
            rows = [r for r in rows if r.get(field) is not None]
        if self._limit is not None:
            rows = rows[: self._limit]
        return rows

    def execute(self):
        if self._insert_data is not None:
            self._rows_ref.append(dict(self._insert_data))
            return _FakeResult([self._insert_data])
        matched = self._matched()
        if self._update_data is not None:
            for r in matched:
                r.update(self._update_data)
            return _FakeResult(copy.deepcopy(matched))
        return _FakeResult(copy.deepcopy(matched))


class _NotFilter:
    def __init__(self, query: _FakeQuery):
        self._query = query

    def is_(self, field, _value):
        self._query._not_is_null_filters.append(field)
        return self._query


class _FakeResult:
    def __init__(self, data):
        self.data = data


class FakeSupabaseClient:
    def __init__(self, entreprises=None, documents=None):
        self._entreprises = entreprises or []
        self._documents = documents or []

    def table(self, name):
        if name == "entreprises":
            return _FakeQuery(self._entreprises)
        if name == "documents":
            return _FakeQuery(self._documents)
        raise AssertionError(f"table inattendue : {name}")


def _make_entreprise(**overrides) -> dict:
    base = dict(
        user_id="user-1",
        compteur_devis=5,
        compteur_devis_annee=2026,
        devis_numero_debut=1,
        devis_numero_prefixe="DEV-",
        devis_numero_inclure_annee=True,
        devis_numero_padding=3,
        compteur_factures=17,
        compteur_factures_annee=2026,
        facture_numero_debut=1,
        facture_numero_prefixe="FAC-",
        facture_numero_inclure_annee=True,
        facture_numero_padding=3,
        numero_reset_annuel=True,
    )
    base.update(overrides)
    return base


def test_preview_next_compteur_devis_et_facture_sont_independants(monkeypatch):
    """Le compteur devis (5→6) ne doit jamais influencer le compteur facture (17→18)."""
    fake = FakeSupabaseClient(entreprises=[_make_entreprise()])
    monkeypatch.setattr("app.services.numero_service.get_supabase_admin", lambda: fake)

    assert preview_next_compteur("user-1", "devis") == 6
    assert preview_next_compteur("user-1", "facture") == 18


# ── Verrouillage backend du point de départ (piège #2) ───────────────────────

def test_numero_debut_non_verrouille_si_aucun_numero_attribue(monkeypatch):
    fake = FakeSupabaseClient(documents=[
        {"user_id": "user-1", "type_doc": "devis", "numero": None},
    ])
    assert profile_router._numero_debut_locked(fake, "user-1", "devis") is False


def test_numero_debut_verrouille_des_qu_un_numero_existe(monkeypatch):
    fake = FakeSupabaseClient(documents=[
        {"user_id": "user-1", "type_doc": "devis", "numero": "DEV-2026-001"},
    ])
    assert profile_router._numero_debut_locked(fake, "user-1", "devis") is True


def test_put_profile_refuse_changement_point_de_depart_si_verrouille(monkeypatch):
    fake = FakeSupabaseClient(
        entreprises=[_make_entreprise(devis_numero_debut=1)],
        documents=[{"user_id": "user-1", "type_doc": "devis", "numero": "DEV-2026-001"}],
    )
    monkeypatch.setattr(profile_router, "get_supabase_admin", lambda: fake)

    class _FakeUser:
        user_id = "user-1"

    nouveau_profil = ProfileEntreprise(devis_numero_debut=2001)  # tentative de changement

    with pytest.raises(HTTPException) as exc:
        profile_router.put_profile(nouveau_profil, current_user=_FakeUser())
    assert exc.value.status_code == 409


def test_put_profile_autorise_changement_point_de_depart_si_non_verrouille(monkeypatch):
    fake = FakeSupabaseClient(
        entreprises=[_make_entreprise(devis_numero_debut=1)],
        documents=[],  # aucun numéro attribué → pas verrouillé
    )
    monkeypatch.setattr(profile_router, "get_supabase_admin", lambda: fake)

    class _FakeUser:
        user_id = "user-1"

    nouveau_profil = ProfileEntreprise(devis_numero_debut=2001)

    result = profile_router.put_profile(nouveau_profil, current_user=_FakeUser())
    assert result.devis_numero_debut == 2001
