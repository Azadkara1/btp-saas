"""
Tests de get_dashboard_stats_raw() (backend/app/services/dashboard_service.py)
— jamais couvert jusqu'ici (trouvé par revue de code, Batch 16). Normalisation
défensive du retour RPC, même pattern que numero_service.py.
"""
import pytest
from fastapi import HTTPException

from app.services.dashboard_service import get_dashboard_stats_raw


class _FakeRpcResult:
    def __init__(self, data):
        self.data = data


class _FakeRpcBuilder:
    def __init__(self, data, raise_on_execute=False):
        self._data = data
        self._raise = raise_on_execute

    def execute(self):
        if self._raise:
            raise Exception("panne réseau simulée")
        return _FakeRpcResult(self._data)


class FakeSupabaseClient:
    def __init__(self, data=None, raise_on_execute=False):
        self._data = data
        self._raise = raise_on_execute

    def rpc(self, _name, _params):
        return _FakeRpcBuilder(self._data, raise_on_execute=self._raise)


def test_get_dashboard_stats_raw_dict_direct(monkeypatch):
    payload = {"ca_signe": 1000.0, "taux_conversion": 50.0}
    fake = FakeSupabaseClient(data=payload)
    monkeypatch.setattr("app.services.dashboard_service.get_supabase_admin", lambda: fake)

    assert get_dashboard_stats_raw("user-1") == payload


def test_get_dashboard_stats_raw_liste_de_dict(monkeypatch):
    payload = {"ca_signe": 2000.0}
    fake = FakeSupabaseClient(data=[payload])
    monkeypatch.setattr("app.services.dashboard_service.get_supabase_admin", lambda: fake)

    assert get_dashboard_stats_raw("user-1") == payload


def test_get_dashboard_stats_raw_liste_vide_retourne_dict_vide(monkeypatch):
    fake = FakeSupabaseClient(data=[])
    monkeypatch.setattr("app.services.dashboard_service.get_supabase_admin", lambda: fake)

    assert get_dashboard_stats_raw("user-1") == {}


def test_get_dashboard_stats_raw_enveloppe_nommee_deballee(monkeypatch):
    """PostgREST peut envelopper le jsonb dans [{"get_dashboard_stats": {...}}]."""
    payload = {"ca_signe": 3000.0}
    fake = FakeSupabaseClient(data=[{"get_dashboard_stats": payload}])
    monkeypatch.setattr("app.services.dashboard_service.get_supabase_admin", lambda: fake)

    assert get_dashboard_stats_raw("user-1") == payload


def test_get_dashboard_stats_raw_type_inattendu_retourne_dict_vide(monkeypatch):
    fake = FakeSupabaseClient(data="pas un dict")
    monkeypatch.setattr("app.services.dashboard_service.get_supabase_admin", lambda: fake)

    assert get_dashboard_stats_raw("user-1") == {}


def test_get_dashboard_stats_raw_echec_reseau_leve_500_sans_fuiter_le_detail(monkeypatch):
    fake = FakeSupabaseClient(raise_on_execute=True)
    monkeypatch.setattr("app.services.dashboard_service.get_supabase_admin", lambda: fake)

    with pytest.raises(HTTPException) as exc:
        get_dashboard_stats_raw("user-1")
    assert exc.value.status_code == 500
    assert "panne réseau simulée" not in str(exc.value.detail)
