"""
Tests de get_next_numero() (backend/app/services/numero_service.py) — la RPC
Postgres atomique qui attribue le numéro légal définitif. Jamais testée
jusqu'ici (trouvé par revue de code, Batch 16) alors que c'est le chemin le
plus sensible de toute la numérotation : normalisation défensive du retour
RPC (str | list[dict] | list[str] selon la version de PostgREST).
"""
import pytest
from fastapi import HTTPException

from app.services.numero_service import get_next_numero


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
    """Ne supporte que .rpc(...).execute() — c'est tout ce que get_next_numero utilise."""
    def __init__(self, data=None, raise_on_execute=False):
        self._data = data
        self._raise = raise_on_execute
        self.last_call = None  # (name, params) — pour vérifier les arguments transmis

    def rpc(self, name, params):
        self.last_call = (name, params)
        return _FakeRpcBuilder(self._data, raise_on_execute=self._raise)


def test_get_next_numero_reponse_str_directe(monkeypatch):
    """Forme la plus simple : PostgREST renvoie le scalaire text directement."""
    fake = FakeSupabaseClient(data="DEV-2026-001")
    monkeypatch.setattr("app.services.numero_service.get_supabase_admin", lambda: fake)

    assert get_next_numero("user-1", "devis") == "DEV-2026-001"
    assert fake.last_call == ("get_next_numero", {"p_user_id": "user-1", "p_type": "devis"})


def test_get_next_numero_reponse_liste_de_dict(monkeypatch):
    """Certaines versions de PostgREST enveloppent le retour d'une fonction
    scalaire dans [{"get_next_numero": "..."}]."""
    fake = FakeSupabaseClient(data=[{"get_next_numero": "FAC-2026-042"}])
    monkeypatch.setattr("app.services.numero_service.get_supabase_admin", lambda: fake)

    assert get_next_numero("user-1", "facture") == "FAC-2026-042"


def test_get_next_numero_reponse_liste_de_str(monkeypatch):
    fake = FakeSupabaseClient(data=["DEV-2026-007"])
    monkeypatch.setattr("app.services.numero_service.get_supabase_admin", lambda: fake)

    assert get_next_numero("user-1", "devis") == "DEV-2026-007"


def test_get_next_numero_liste_vide_leve_500(monkeypatch):
    fake = FakeSupabaseClient(data=[])
    monkeypatch.setattr("app.services.numero_service.get_supabase_admin", lambda: fake)

    with pytest.raises(HTTPException) as exc:
        get_next_numero("user-1", "devis")
    assert exc.value.status_code == 500


def test_get_next_numero_type_inattendu_leve_500(monkeypatch):
    """Un nombre, un None ou une chaîne vide ne doivent jamais être renvoyés
    comme numéro légal silencieusement."""
    for donnee_invalide in (None, 42, ""):
        fake = FakeSupabaseClient(data=donnee_invalide)
        monkeypatch.setattr("app.services.numero_service.get_supabase_admin", lambda f=fake: f)
        with pytest.raises(HTTPException) as exc:
            get_next_numero("user-1", "devis")
        assert exc.value.status_code == 500


def test_get_next_numero_echec_reseau_leve_500_sans_fuiter_le_detail(monkeypatch):
    """Ne doit jamais exposer le message d'exception brut au client
    (cf. correctif Batch 16 sur les messages d'erreur)."""
    fake = FakeSupabaseClient(raise_on_execute=True)
    monkeypatch.setattr("app.services.numero_service.get_supabase_admin", lambda: fake)

    with pytest.raises(HTTPException) as exc:
        get_next_numero("user-1", "devis")
    assert exc.value.status_code == 500
    assert "panne réseau simulée" not in str(exc.value.detail)
