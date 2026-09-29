"""
Tests du rate limiter en mémoire (backend/app/routers/quotes.py) — Batch 16 :
purge des IP inactives (fuite mémoire lente) et respect de X-Forwarded-For
derrière le proxy de Render (sans quoi la limite "10 req/min par IP"
deviendrait une limite globale partagée par tous les utilisateurs).
"""
import pytest

from app.routers import quotes as quotes_router


@pytest.fixture(autouse=True)
def _reset_rate_store():
    quotes_router._rate_store.clear()
    yield
    quotes_router._rate_store.clear()


# ── _check_rate_limit ────────────────────────────────────────────────────────

def test_check_rate_limit_autorise_sous_la_limite():
    for _ in range(quotes_router._RATE_LIMIT):
        assert quotes_router._check_rate_limit("1.2.3.4") is True


def test_check_rate_limit_bloque_au_dela_de_la_limite():
    for _ in range(quotes_router._RATE_LIMIT):
        quotes_router._check_rate_limit("1.2.3.4")
    assert quotes_router._check_rate_limit("1.2.3.4") is False


def test_check_rate_limit_ip_independantes():
    for _ in range(quotes_router._RATE_LIMIT):
        quotes_router._check_rate_limit("1.2.3.4")
    assert quotes_router._check_rate_limit("1.2.3.4") is False
    assert quotes_router._check_rate_limit("5.6.7.8") is True  # IP différente, jamais affectée


def test_check_rate_limit_purge_les_ip_a_fenetre_expiree(monkeypatch):
    """Avant le correctif, une IP vue une seule fois restait indéfiniment
    dans _rate_store (fuite mémoire lente sur la durée de vie du process)."""
    from datetime import datetime as real_datetime, timedelta

    class _StaleDatetime:
        @staticmethod
        def utcnow():
            return real_datetime.utcnow() - timedelta(seconds=quotes_router._RATE_WINDOW + 5)

    monkeypatch.setattr(quotes_router, "datetime", _StaleDatetime)
    quotes_router._check_rate_limit("9.9.9.9")
    monkeypatch.undo()  # revient au vrai datetime pour la suite du test

    assert "9.9.9.9" in quotes_router._rate_store  # pas encore purgée, personne n'a rappelé la fonction

    quotes_router._check_rate_limit("1.2.3.4")  # déclenche la purge globale, en temps réel
    assert "9.9.9.9" not in quotes_router._rate_store


# ── _get_client_ip ────────────────────────────────────────────────────────────

class _FakeClient:
    def __init__(self, host):
        self.host = host


class _FakeRequest:
    def __init__(self, headers=None, client_host="127.0.0.1"):
        self.headers = headers or {}
        self.client = _FakeClient(client_host)


def test_get_client_ip_utilise_x_forwarded_for_si_present():
    """Derrière le proxy Render, req.client.host reflète l'IP du proxy, pas
    du visiteur — X-Forwarded-For doit primer."""
    req = _FakeRequest(headers={"x-forwarded-for": "203.0.113.5, 10.0.0.1"}, client_host="10.0.0.1")
    assert quotes_router._get_client_ip(req) == "203.0.113.5"


def test_get_client_ip_fallback_sur_req_client_host_si_absent():
    req = _FakeRequest(headers={}, client_host="192.168.1.10")
    assert quotes_router._get_client_ip(req) == "192.168.1.10"
