"""
Tests des corrections Batch 16 :
- validation serveur des transitions de statut (_statut_transition_update)
- PUT /documents/{id} restreint aux brouillons (persistance des éditions)
- convert_to_facture ne doit jamais avaler silencieusement une erreur de
  recherche d'acomptes déjà facturés (risque de double facturation)
"""
import copy

import pytest
from fastapi import HTTPException

from app.models.document import DocumentCreate
from app.routers import documents as documents_router


# ── Faux client Supabase (documents + clients) ──────────────────────────────

class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, rows_ref):
        self._rows_ref = rows_ref
        self._eq_filters = []
        self._is_null_filters = []
        self._update_data = None
        self._insert_data = None

    def select(self, *_a, **_k):
        return self

    def eq(self, field, value):
        self._eq_filters.append((field, value))
        return self

    def is_(self, field, _value):
        self._is_null_filters.append(field)
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
        for field in self._is_null_filters:
            rows = [r for r in rows if r.get(field) is None]
        return rows

    def execute(self):
        if self._insert_data is not None:
            row = dict(self._insert_data)
            row.setdefault("id", "new-id")
            self._rows_ref.append(row)
            return _FakeResult([row])
        matched = self._matched()
        if self._update_data is not None:
            for r in matched:
                r.update(self._update_data)
        return _FakeResult(copy.deepcopy(matched))


class _FailingQuery(_FakeQuery):
    def execute(self):
        raise Exception("panne réseau simulée")


class FakeSupabaseClient:
    def __init__(self, documents=None, clients=None):
        self._documents = documents or []
        self._clients = clients or []

    def table(self, name):
        if name == "documents":
            return _FakeQuery(self._documents)
        if name == "clients":
            return _FakeQuery(self._clients)
        raise AssertionError(f"table inattendue : {name}")


class _FakeCurrentUser:
    def __init__(self, user_id):
        self.user_id = user_id


def _make_doc(**overrides):
    base = dict(
        id="doc-1", user_id="user-1", type_doc="devis", statut="envoyé",
        numero=None, date_envoi=None, date_signature=None, date_paiement=None,
        date_refus=None, date_expiration=None,
    )
    base.update(overrides)
    return base


# ── Validation des transitions de statut (BLOQUANT #2) ──────────────────────

def test_transition_autorisee_ne_leve_pas():
    doc = _make_doc(statut="envoyé")
    update_data = documents_router._statut_transition_update("user-1", doc, "signé")
    assert update_data["statut"] == "signé"


def test_transition_brouillon_vers_paye_refusee():
    """Sans validation, un appel API direct pouvait marquer un brouillon
    'payé' sans jamais lui attribuer de numéro légal."""
    doc = _make_doc(statut="brouillon")
    with pytest.raises(HTTPException) as exc:
        documents_router._statut_transition_update("user-1", doc, "payé")
    assert exc.value.status_code == 409


def test_transition_brouillon_vers_signe_refusee():
    """Un devis 'signé' sans passer par la signature électronique (nom,
    image, IP) serait un faux positif légal — doit être bloqué."""
    doc = _make_doc(statut="brouillon")
    with pytest.raises(HTTPException) as exc:
        documents_router._statut_transition_update("user-1", doc, "signé")
    assert exc.value.status_code == 409


def test_transition_arriere_paye_vers_brouillon_refusee():
    doc = _make_doc(statut="payé", numero="FAC-2026-001")
    with pytest.raises(HTTPException) as exc:
        documents_router._statut_transition_update("user-1", doc, "brouillon")
    assert exc.value.status_code == 409


def test_transition_envoye_vers_envoye_autorisee_reenvoi():
    """POST /documents/{id}/send doit pouvoir renvoyer l'email sans échouer."""
    doc = _make_doc(statut="envoyé")
    update_data = documents_router._statut_transition_update("user-1", doc, "envoyé")
    assert update_data["statut"] == "envoyé"


def test_transition_signe_vers_envoye_refusee_ne_regresse_pas():
    """Un /send appelé sur un devis déjà signé ne doit jamais le faire
    régresser à 'envoyé'."""
    doc = _make_doc(statut="signé", date_signature="2026-08-10T00:00:00+00:00")
    with pytest.raises(HTTPException) as exc:
        documents_router._statut_transition_update("user-1", doc, "envoyé")
    assert exc.value.status_code == 409


def test_transition_terminale_ne_permet_plus_rien():
    for statut_terminal in ("payé", "refusé", "expiré"):
        doc = _make_doc(statut=statut_terminal)
        for cible in ("brouillon", "envoyé", "signé", "payé", "refusé", "expiré"):
            if cible == statut_terminal:
                continue
            with pytest.raises(HTTPException):
                documents_router._statut_transition_update("user-1", doc, cible)


# ── PUT /documents/{id} — persistance du contenu (Batch 16) ─────────────────

def _make_document_create(**overrides):
    base = dict(
        type_doc="devis",
        titre="Devis Test",
        numero_document="DEV-2026-001",
        date_document="2026-08-25",
        devis_payload={
            "client": {"nom": "Client"}, "chantier": {"description": "x"},
            "lignes": [], "totaux": {"total_ht": 0, "total_tva": 0, "total_ttc": 0},
            "mentions_legales": [],
        },
        total_ttc=0,
        client_nom=None, client_adresse=None, client_code_postal=None, client_ville=None,
    )
    base.update(overrides)
    return DocumentCreate(**base)


def _make_full_doc_row(**overrides):
    base = dict(
        id="doc-1", user_id="user-1", statut="brouillon", client_id=None,
        type_doc="devis", titre="x", numero=None, numero_document=None,
        date_document="2026-08-25", devis_payload={}, total_ttc=0,
        created_at="2026-08-25T00:00:00+00:00", document_source_id=None,
        date_envoi=None, date_signature=None, date_paiement=None,
        date_refus=None, date_expiration=None, date_email_envoye=None,
        email_destinataire=None, signature_nom_signataire=None,
        signature_image_base64=None,
    )
    base.update(overrides)
    return base


def test_put_document_content_reussit_sur_brouillon(monkeypatch):
    doc_row = _make_full_doc_row()
    fake = FakeSupabaseClient(documents=[doc_row])
    monkeypatch.setattr(documents_router, "get_supabase_admin", lambda: fake)

    result = documents_router.update_document_content(
        "doc-1", _make_document_create(titre="Nouveau titre"), current_user=_FakeCurrentUser("user-1")
    )
    assert result.titre == "Nouveau titre"
    assert doc_row["titre"] == "Nouveau titre"


def test_put_document_content_refuse_si_pas_brouillon(monkeypatch):
    doc_row = _make_full_doc_row(statut="envoyé")
    fake = FakeSupabaseClient(documents=[doc_row])
    monkeypatch.setattr(documents_router, "get_supabase_admin", lambda: fake)

    with pytest.raises(HTTPException) as exc:
        documents_router.update_document_content(
            "doc-1", _make_document_create(), current_user=_FakeCurrentUser("user-1")
        )
    assert exc.value.status_code == 409
    assert doc_row["titre"] == "x"  # inchangé


def test_put_document_content_404_si_autre_utilisateur(monkeypatch):
    doc_row = _make_full_doc_row(user_id="user-1")
    fake = FakeSupabaseClient(documents=[doc_row])
    monkeypatch.setattr(documents_router, "get_supabase_admin", lambda: fake)

    with pytest.raises(HTTPException) as exc:
        documents_router.update_document_content(
            "doc-1", _make_document_create(), current_user=_FakeCurrentUser("user-2")
        )
    assert exc.value.status_code == 404


# ── convert_to_facture — échec silencieux du calcul d'acompte (BLOQUANT #3) ─

def test_convert_to_facture_leve_erreur_explicite_si_recherche_acompte_echoue(monkeypatch):
    """Avant le correctif, une panne réseau ici faisait retomber silencieusement
    montant_deja_verse à 0 -> double facturation possible. Doit désormais lever
    une erreur explicite plutôt que de continuer comme si de rien n'était."""
    doc_row = {
        "id": "doc-1", "user_id": "user-1", "type_doc": "devis", "statut": "signé",
        "titre": "Devis Test", "client_id": None, "numero_document": "DEV-2026-001",
        "date_document": "2026-08-25",
        "devis_payload": {
            "client": {"nom": "Client"}, "artisan": {}, "chantier": {"description": "x"},
            "lignes": [], "totaux": {"total_ht": 100, "total_tva": 20, "total_ttc": 120},
            "mentions_legales": [],
        },
        "total_ttc": 120,
    }

    class _ClientWithFailingSecondCall:
        """1er appel table("documents") = _fetch_source_document (doit réussir).
        2e appel = recherche des factures d'acompte (doit échouer)."""
        def __init__(self, rows):
            self._rows = rows
            self._calls = 0

        def table(self, name):
            assert name == "documents"
            self._calls += 1
            if self._calls == 1:
                return _FakeQuery(self._rows)
            return _FailingQuery(self._rows)

    monkeypatch.setattr(
        documents_router, "get_supabase_admin", lambda: _ClientWithFailingSecondCall([doc_row])
    )

    with pytest.raises(HTTPException) as exc:
        documents_router.convert_to_facture("doc-1", current_user=_FakeCurrentUser("user-1"))
    assert exc.value.status_code == 500
