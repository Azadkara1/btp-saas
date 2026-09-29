"""
Tests de send_devis_email() (backend/app/services/email_service.py) — jamais
couvert jusqu'ici (trouvé par revue de code, Batch 16). Comportement bloquant
volontaire (piège documenté dans CLAUDE.md) : cette fonction DOIT lever une
HTTPException si l'envoi échoue, pour que POST /documents/{id}/send n'écrive
jamais en base ni ne gaspille de numéro légal.
"""
import pytest
from fastapi import HTTPException

from app.services import email_service


class _FakeSettings:
    def __init__(self, resend_api_key="re_test_key", resend_from_email="test@example.com"):
        self.resend_api_key = resend_api_key
        self.resend_from_email = resend_from_email


class _FakeResponse:
    def __init__(self, status_code=200, text="OK"):
        self.status_code = status_code
        self.text = text


def test_send_devis_email_leve_500_si_api_key_absente(monkeypatch):
    monkeypatch.setattr(email_service, "get_settings", lambda: _FakeSettings(resend_api_key=""))

    with pytest.raises(HTTPException) as exc:
        email_service.send_devis_email("client@test.fr", "Sujet", "<p>Corps</p>", b"%PDF-1.4", "devis.pdf")
    assert exc.value.status_code == 500


def test_send_devis_email_succes_appelle_resend_avec_le_bon_payload(monkeypatch):
    calls = []

    def _fake_post(url, json, headers, timeout):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return _FakeResponse(status_code=200)

    monkeypatch.setattr(email_service, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(email_service.httpx, "post", _fake_post)

    email_service.send_devis_email("client@test.fr", "Votre devis", "<p>Bonjour</p>", b"%PDF-1.4", "devis.pdf")

    assert len(calls) == 1
    payload = calls[0]["json"]
    assert payload["to"] == ["client@test.fr"]
    assert payload["subject"] == "Votre devis"
    assert payload["attachments"][0]["filename"] == "devis.pdf"
    assert calls[0]["headers"]["Authorization"] == "Bearer re_test_key"


def test_send_devis_email_leve_502_si_resend_refuse(monkeypatch):
    monkeypatch.setattr(email_service, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(
        email_service.httpx, "post",
        lambda *a, **k: _FakeResponse(status_code=422, text="adresse invalide"),
    )

    with pytest.raises(HTTPException) as exc:
        email_service.send_devis_email("mauvaise-adresse", "Sujet", "<p>x</p>", b"%PDF-1.4", "devis.pdf")
    assert exc.value.status_code == 502


def test_send_devis_email_leve_502_si_panne_reseau(monkeypatch):
    import httpx as real_httpx

    def _raise(*_a, **_k):
        raise real_httpx.RequestError("connexion refusée")

    monkeypatch.setattr(email_service, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(email_service.httpx, "post", _raise)

    with pytest.raises(HTTPException) as exc:
        email_service.send_devis_email("client@test.fr", "Sujet", "<p>x</p>", b"%PDF-1.4", "devis.pdf")
    assert exc.value.status_code == 502
