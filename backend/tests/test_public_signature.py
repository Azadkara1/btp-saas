"""
Tests de la signature électronique publique (Batch 12 T3).

Aucune base de données réelle : un faux client Supabase en mémoire simule la
table `documents` pour tester la logique métier (token invalide, devis déjà
signé, devis expiré, filtrage user_id) sans dépendance externe — la CI
(Batch 12 T2) doit rester exécutable sans secrets.
"""
import copy
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.models.public import AcceptSignatureRequest
from app.routers import documents as documents_router
from app.routers import public as public_router


# ── Faux client Supabase (juste ce dont ces deux routeurs ont besoin) ───────

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
        # seul usage dans le projet : is_("deleted_at", "null") → IS NULL
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
    def __init__(self, rows):
        self._documents = rows

    def table(self, name):
        assert name == "documents"
        return _FakeQuery(self._documents)


class _FakeRequest:
    """Simule fastapi.Request pour accept_devis (IP + user-agent)."""
    client = None
    headers = {}


class _FakeCurrentUser:
    def __init__(self, user_id: str):
        self.user_id = user_id


def _make_doc(**overrides) -> dict:
    base = {
        "id": "doc-1",
        "user_id": "user-1",
        "type_doc": "devis",
        "statut": "envoyé",
        "numero": None,
        "numero_document": "DEVIS-001",
        "date_document": "2026-08-01",
        "date_envoi": "2026-08-01T00:00:00+00:00",
        "date_signature": None,
        "date_paiement": None,
        "date_refus": None,
        "date_expiration": None,
        "deleted_at": None,
        "signature_token": "tok-abc123",
        "signature_token_expires_at": None,
        "signature_nom_signataire": None,
        "devis_payload": {
            "client": {"nom": "Client Test"},
            "artisan": {
                "nom": "Artisan Test",
                "iban": "FR7630006000011234567890189",
                "bic": "BNPAFRPPXXX",
                "email": "artisan@test.fr",
            },
            "chantier": {"description": "Chantier test"},
            "lignes": [{
                "poste": "P", "description": "D", "quantite": 1, "unite": "u",
                "prix_unitaire_ht": 100, "tva_taux": 20, "source_prix": "estimation",
            }],
            "totaux": {"total_ht": 100, "total_tva": 20, "total_ttc": 120},
            "mentions_legales": [],
        },
    }
    base.update(overrides)
    return base


# ── Logique pure (aucune DB) ────────────────────────────────────────────────

def test_is_signable_seulement_si_envoye():
    assert public_router._is_signable("envoyé") is True
    for statut in ["brouillon", "signé", "refusé", "expiré", "payé"]:
        assert public_router._is_signable(statut) is False


# ── Token invalide / expiré ──────────────────────────────────────────────────

def test_token_invalide_renvoie_404(monkeypatch):
    fake = FakeSupabaseClient([_make_doc()])
    monkeypatch.setattr(public_router, "get_supabase_admin", lambda: fake)

    with pytest.raises(HTTPException) as exc:
        public_router._fetch_by_token("token-qui-nexiste-pas")
    assert exc.value.status_code == 404


def test_devis_expire_renvoie_410(monkeypatch):
    expires_passe = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    doc = _make_doc(signature_token_expires_at=expires_passe)
    fake = FakeSupabaseClient([doc])
    monkeypatch.setattr(public_router, "get_supabase_admin", lambda: fake)

    with pytest.raises(HTTPException) as exc:
        public_router._fetch_by_token("tok-abc123")
    assert exc.value.status_code == 410


# ── Devis déjà signé → refus d'une nouvelle signature (idempotence) ────────

def test_devis_deja_signe_refuse_nouvelle_signature(monkeypatch):
    doc = _make_doc(
        statut="signé",
        date_signature="2026-08-10T00:00:00+00:00",
        signature_nom_signataire="Jean Dupont",
    )
    fake = FakeSupabaseClient([doc])
    monkeypatch.setattr(public_router, "get_supabase_admin", lambda: fake)

    with pytest.raises(HTTPException) as exc:
        public_router.accept_devis(
            "tok-abc123",
            AcceptSignatureRequest(nom_signataire="Autre Personne"),
            request=_FakeRequest(),
        )
    assert exc.value.status_code == 409


def test_devis_expire_refuse_signature(monkeypatch):
    doc = _make_doc(statut="expiré")
    fake = FakeSupabaseClient([doc])
    monkeypatch.setattr(public_router, "get_supabase_admin", lambda: fake)

    with pytest.raises(HTTPException) as exc:
        public_router.accept_devis(
            "tok-abc123",
            AcceptSignatureRequest(nom_signataire="Jean Dupont"),
            request=_FakeRequest(),
        )
    assert exc.value.status_code == 409


# ── La vue publique ne fuite jamais IBAN/BIC/email/user_id ─────────────────

def test_get_public_devis_ne_fuite_jamais_infos_sensibles(monkeypatch):
    fake = FakeSupabaseClient([_make_doc()])
    monkeypatch.setattr(public_router, "get_supabase_admin", lambda: fake)

    view = public_router.get_public_devis("tok-abc123")
    dumped = view.model_dump()

    assert "iban" not in dumped["artisan"]
    assert "bic" not in dumped["artisan"]
    assert "email" not in dumped["artisan"]
    assert "user_id" not in dumped
    assert dumped["artisan"]["nom"] == "Artisan Test"  # le reste passe bien


# ── Accès croisé entre utilisateurs (lien de signature) ─────────────────────

def test_signature_link_refuse_document_dun_autre_utilisateur(monkeypatch):
    doc = _make_doc(user_id="user-1")
    fake = FakeSupabaseClient([doc])
    monkeypatch.setattr(documents_router, "get_supabase_admin", lambda: fake)

    with pytest.raises(HTTPException) as exc:
        documents_router.get_signature_link("doc-1", current_user=_FakeCurrentUser("user-2"))
    assert exc.value.status_code == 404


def test_signature_link_genere_le_token_si_absent(monkeypatch):
    doc = _make_doc(signature_token=None, signature_token_expires_at=None)
    fake = FakeSupabaseClient([doc])
    monkeypatch.setattr(documents_router, "get_supabase_admin", lambda: fake)

    # get_settings() exigerait ANTHROPIC_API_KEY/SUPABASE_SERVICE_ROLE_KEY réels
    # (champs requis, sans défaut) — hors de propos ici, on ne teste que
    # frontend_url. Simple bouchon pour rester indépendant de tout secret,
    # conformément à la CI (Batch 12 T2).
    class _FakeSettings:
        frontend_url = "https://example.test"

    monkeypatch.setattr(documents_router, "get_settings", lambda: _FakeSettings())

    result = documents_router.get_signature_link("doc-1", current_user=_FakeCurrentUser("user-1"))

    assert result["url"].startswith("http")
    assert doc["signature_token"] is not None
    assert doc["signature_token_expires_at"] is not None


# ── Notification email artisan à la signature (Batch 14) ────────────────────
# Best-effort : ne doit jamais faire échouer la signature elle-même, que ce
# soit un email artisan absent ou un échec d'envoi (Resend non configuré,
# panne réseau...). La signature en base reste la seule chose garantie.

def test_accept_devis_reussit_meme_si_email_non_configure(monkeypatch):
    """RESEND_API_KEY absente en environnement de test → send_devis_email lève,
    mais accept_devis doit quand même renvoyer un succès."""
    doc = _make_doc()
    fake = FakeSupabaseClient([doc])
    monkeypatch.setattr(public_router, "get_supabase_admin", lambda: fake)

    result = public_router.accept_devis(
        "tok-abc123",
        AcceptSignatureRequest(nom_signataire="Jean Dupont"),
        request=_FakeRequest(),
    )
    assert result.statut == "signé"


def test_notifier_artisan_signature_sans_email_ne_leve_pas():
    doc = _make_doc()
    doc["devis_payload"]["artisan"]["email"] = None
    public_router._notifier_artisan_signature(doc, {"signature_nom_signataire": "Jean Dupont"})


def test_notifier_artisan_signature_appelle_send_devis_email_avec_le_bon_destinataire(monkeypatch):
    calls = []
    monkeypatch.setattr(public_router, "send_devis_email", lambda **kwargs: calls.append(kwargs))

    doc = _make_doc()
    public_router._notifier_artisan_signature(doc, {
        "signature_nom_signataire": "Jean Dupont",
        "date_signature": "2026-08-25T12:00:00+00:00",
    })

    assert len(calls) == 1
    assert calls[0]["to"] == "artisan@test.fr"
    assert "Jean Dupont" in calls[0]["subject"]
    assert len(calls[0]["pdf_bytes"]) > 0


def test_notifier_artisan_signature_echec_envoi_ne_leve_pas(monkeypatch):
    def _fake_send(**_kwargs):
        raise Exception("Resend down")
    monkeypatch.setattr(public_router, "send_devis_email", _fake_send)

    doc = _make_doc()
    public_router._notifier_artisan_signature(doc, {"signature_nom_signataire": "Jean Dupont"})
