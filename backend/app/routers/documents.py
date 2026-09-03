"""
Routeur documents — Lots 3 & 4 + Phase 2 (conversion & duplication) + Batch 11.

POST   /documents                  → auto-save brouillon post-génération + upsert client
GET    /documents                  → historique de l'utilisateur (colonnes indexées)
GET    /documents/{id}             → Devis complet pour réouverture
PATCH  /documents/{id}             → mise à jour statut ; brouillon→envoyé attribue le numéro
POST   /documents/{id}/convert     → duplique un devis signé en facture brouillon (filiation)
POST   /documents/{id}/duplicate   → duplique un document à l'identique (même type_doc)
POST   /documents/{id}/create-acompte → génère une facture d'acompte à partir d'un devis signé
DELETE /documents/{id}             → soft delete (deleted_at) ; refuse si statut hors brouillon/refusé
POST   /documents/{id}/send        → génère le PDF, l'archive, l'envoie par email, transition → envoyé
GET    /documents/{id}/signature-link → génère (si absent) et renvoie le lien public de signature

⚠️  Client service_role : filtrage user_id obligatoire sur chaque requête.
⚠️  Jamais de DELETE physique — un document ayant reçu un numéro légal ne doit
    jamais disparaître de la table (soft delete via deleted_at uniquement).
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user, CurrentUser
from app.core.config import get_settings

logger = logging.getLogger(__name__)
from app.core.supabase_client import get_supabase_admin
from app.models.document import (
    CreateAcompteRequest,
    DocumentCreate,
    DocumentDetail,
    DocumentSummary,
    SendEmailRequest,
    SendEmailResponse,
    StatusUpdate,
    StatusPatchResponse,
)
from app.models.quote import Devis, LigneDevis, SourcePrix, TotauxDevis
from app.services.email_service import send_devis_email
from app.services.numero_service import get_next_numero
from app.services.pdf_service import generate_quote_pdf
from app.services.storage_service import archive_document_pdf

router = APIRouter()


def _row_to_detail(row: dict, client_nom: str | None) -> DocumentDetail:
    """Construit un DocumentDetail à partir d'une ligne brute Supabase."""
    return DocumentDetail(
        id=row["id"],
        type_doc=row["type_doc"],
        titre=row.get("titre"),
        numero=row.get("numero"),
        numero_document=row.get("numero_document"),
        client_nom=client_nom,
        total_ttc=float(row["total_ttc"]) if row.get("total_ttc") is not None else None,
        statut=row["statut"],
        date_document=str(row["date_document"]) if row.get("date_document") else None,
        created_at=str(row["created_at"]),
        document_source_id=row.get("document_source_id"),
        date_envoi=row.get("date_envoi"),
        date_signature=row.get("date_signature"),
        date_paiement=row.get("date_paiement"),
        date_refus=row.get("date_refus"),
        date_expiration=row.get("date_expiration"),
        date_email_envoye=row.get("date_email_envoye"),
        email_destinataire=row.get("email_destinataire"),
        signature_nom_signataire=row.get("signature_nom_signataire"),
        signature_image_base64=row.get("signature_image_base64"),
        devis_payload=row["devis_payload"],
    )


# ── POST /documents ─────────────────────────────────────────────────────────

@router.post("", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
def create_document(
    body: DocumentCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = current_user.user_id
    db = get_supabase_admin()

    # ① Upsert client (clé : user_id + nom)
    client_id = None
    if body.client_nom:
        try:
            existing_client = (
                db.table("clients")
                .select("id")
                .eq("user_id", uid)
                .eq("nom", body.client_nom)
                .execute()
            )
            if existing_client.data:
                client_id = existing_client.data[0]["id"]
                db.table("clients").update({
                    "adresse": body.client_adresse,
                    "code_postal": body.client_code_postal,
                    "ville": body.client_ville,
                }).eq("id", client_id).eq("user_id", uid).execute()
            else:
                ins = db.table("clients").insert({
                    "user_id": uid,
                    "nom": body.client_nom,
                    "adresse": body.client_adresse,
                    "code_postal": body.client_code_postal,
                    "ville": body.client_ville,
                }).execute()
                client_id = ins.data[0]["id"]
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    # ② Insert document en brouillon
    try:
        ins = db.table("documents").insert({
            "user_id": uid,
            "client_id": client_id,
            "type_doc": body.type_doc,
            "titre": body.titre,
            "numero_document": body.numero_document,
            "date_document": body.date_document,
            "devis_payload": body.devis_payload,
            "total_ttc": body.total_ttc,
            "statut": "brouillon",
        }).execute()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    row = ins.data[0]
    return _row_to_detail(row, body.client_nom)


# ── GET /documents ───────────────────────────────────────────────────────────

@router.get("", response_model=list[DocumentSummary])
def list_documents(current_user: CurrentUser = Depends(get_current_user)):
    uid = current_user.user_id
    db = get_supabase_admin()

    try:
        docs_res = (
            db.table("documents")
            .select(
                "id, type_doc, titre, numero, numero_document, client_id, total_ttc, "
                "statut, date_document, created_at, document_source_id, "
                "date_envoi, date_signature, date_paiement, date_refus, date_expiration, "
                "date_email_envoye, email_destinataire, signature_nom_signataire"
            )
            .eq("user_id", uid)
            .is_("deleted_at", "null")
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    docs = docs_res.data or []

    # Batch-fetch noms clients
    client_ids = list({d["client_id"] for d in docs if d.get("client_id")})
    client_map: dict[str, str] = {}
    if client_ids:
        try:
            clients_res = (
                db.table("clients")
                .select("id, nom")
                .in_("id", client_ids)
                .eq("user_id", uid)
                .execute()
            )
            client_map = {c["id"]: c["nom"] for c in (clients_res.data or [])}
        except Exception:
            pass

    return [
        DocumentSummary(
            id=d["id"],
            type_doc=d["type_doc"],
            titre=d.get("titre"),
            numero=d.get("numero"),
            numero_document=d.get("numero_document"),
            client_nom=client_map.get(d.get("client_id", "")),
            total_ttc=float(d["total_ttc"]) if d.get("total_ttc") is not None else None,
            statut=d["statut"],
            date_document=str(d["date_document"]) if d.get("date_document") else None,
            created_at=str(d["created_at"]),
            document_source_id=d.get("document_source_id"),
            date_envoi=d.get("date_envoi"),
            date_signature=d.get("date_signature"),
            date_paiement=d.get("date_paiement"),
            date_refus=d.get("date_refus"),
            date_expiration=d.get("date_expiration"),
            date_email_envoye=d.get("date_email_envoye"),
            email_destinataire=d.get("email_destinataire"),
            signature_nom_signataire=d.get("signature_nom_signataire"),
        )
        for d in docs
    ]


# ── GET /documents/{id} ──────────────────────────────────────────────────────

@router.get("/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: str, current_user: CurrentUser = Depends(get_current_user)):
    uid = current_user.user_id
    db = get_supabase_admin()

    try:
        res = (
            db.table("documents")
            .select("*")
            .eq("id", doc_id)
            .eq("user_id", uid)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")

    row = res.data[0]

    # Nom du client
    client_nom = None
    if row.get("client_id"):
        try:
            c_res = (
                db.table("clients")
                .select("nom")
                .eq("id", row["client_id"])
                .eq("user_id", uid)
                .execute()
            )
            if c_res.data:
                client_nom = c_res.data[0]["nom"]
        except Exception:
            pass

    return _row_to_detail(row, client_nom)


# ── Helpers Phase 2 : conversion & duplication ──────────────────────────────

def _fetch_source_document(db, doc_id: str, uid: str) -> dict:
    """Récupère un document source (n'importe quel statut) filtré par user_id, ou 404."""
    res = (
        db.table("documents")
        .select("*")
        .eq("id", doc_id)
        .eq("user_id", uid)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")
    return res.data[0]


def _client_nom_for(db, client_id: str | None, uid: str) -> str | None:
    if not client_id:
        return None
    try:
        c_res = db.table("clients").select("nom").eq("id", client_id).eq("user_id", uid).execute()
        if c_res.data:
            return c_res.data[0]["nom"]
    except Exception:
        pass
    return None


# ── POST /documents/{id}/convert ────────────────────────────────────────────
# Transforme un devis (normalement signé) en facture brouillon, en conservant
# la filiation via document_source_id. Le numéro légal sera attribué à l'envoi
# (RPC get_next_numero), donc jamais copié depuis le devis source.
#
# Batch 12 T4-2 : si une ou plusieurs factures d'acompte (T4-1) ont déjà été
# émises pour ce devis, la facture produite ici devient une "facture de solde"
# — déduction affichée dans le PDF/Word (mécanisme `Devis.acompte` existant,
# rien de neuf à y créer) + `net_a_payer` recalculé.

def _apply_montant_deja_verse(devis: Devis, montant_deja_verse: float) -> tuple[Devis, float]:
    """Si un acompte a déjà été facturé séparément (T4-1), transforme le devis
    en facture de solde : déduit ce montant, recalcule le net à payer.
    Retourne (devis mis à jour, total_ttc à stocker en base). Fonction pure —
    testée directement sans base de données, même pattern que `_build_acompte_devis`.

    Le total_ttc retourné est le RESTE À PAYER, pas le total brut du devis :
    la colonne `documents.total_ttc` alimente le CA du dashboard (SUM), et le
    montant de l'acompte y est déjà compté via sa propre facture — le stocker
    une 2e fois ici doublerait le CA affiché.
    """
    if montant_deja_verse <= 0:
        return devis, devis.totaux.total_ttc

    net_a_payer = round(max(0, devis.totaux.total_ttc - montant_deja_verse), 2)
    updated = devis.model_copy(update={
        "type_facture": "solde",
        "acompte": montant_deja_verse,
        "totaux": devis.totaux.model_copy(update={"net_a_payer": net_a_payer}),
    })
    return updated, net_a_payer


@router.post("/{doc_id}/convert", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
def convert_to_facture(doc_id: str, current_user: CurrentUser = Depends(get_current_user)):
    uid = current_user.user_id
    db = get_supabase_admin()

    source = _fetch_source_document(db, doc_id, uid)
    if source["type_doc"] != "devis":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Seul un devis peut être converti en facture")

    titre_source = source.get("titre") or ""
    titre = "Facture" + titre_source[len("Devis"):] if titre_source.lower().startswith("devis") else titre_source

    # Factures d'acompte déjà émises pour ce devis (T4-1) — n'importe quel
    # statut hors supprimé : dès qu'une facture d'acompte existe, l'artisan
    # l'a délibérément créée pour ce montant, elle doit se déduire du solde.
    try:
        acompte_res = (
            db.table("documents")
            .select("total_ttc, devis_payload")
            .eq("document_source_id", doc_id)
            .eq("user_id", uid)
            .eq("type_doc", "facture")
            .is_("deleted_at", "null")
            .execute()
        )
        montant_deja_verse = sum(
            (d.get("total_ttc") or 0)
            for d in (acompte_res.data or [])
            if (d.get("devis_payload") or {}).get("type_facture") == "acompte"
        )
    except Exception:
        montant_deja_verse = 0

    devis = Devis(**source["devis_payload"])
    devis, total_ttc = _apply_montant_deja_verse(devis, montant_deja_verse)

    try:
        ins = db.table("documents").insert({
            "user_id": uid,
            "client_id": source.get("client_id"),
            "type_doc": "facture",
            "titre": titre,
            "numero_document": source.get("numero_document"),
            "date_document": source.get("date_document"),
            "devis_payload": devis.model_dump(),
            "total_ttc": total_ttc,
            "statut": "brouillon",
            "document_source_id": doc_id,
        }).execute()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    row = ins.data[0]
    client_nom = _client_nom_for(db, row.get("client_id"), uid)
    return _row_to_detail(row, client_nom)


# ── POST /documents/{id}/duplicate ──────────────────────────────────────────
# Copie conforme d'un document (même type_doc) pour refaire un chantier
# similaire. Toujours brouillon, toujours sans numéro légal ni filiation.

@router.post("/{doc_id}/duplicate", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
def duplicate_document(doc_id: str, current_user: CurrentUser = Depends(get_current_user)):
    uid = current_user.user_id
    db = get_supabase_admin()

    source = _fetch_source_document(db, doc_id, uid)

    titre_source = source.get("titre") or ""
    titre = f"{titre_source} (copie)" if titre_source else None

    try:
        ins = db.table("documents").insert({
            "user_id": uid,
            "client_id": source.get("client_id"),
            "type_doc": source["type_doc"],
            "titre": titre,
            "numero_document": source.get("numero_document"),
            "date_document": source.get("date_document"),
            "devis_payload": source["devis_payload"],
            "total_ttc": source.get("total_ttc"),
            "statut": "brouillon",
        }).execute()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    row = ins.data[0]
    client_nom = _client_nom_for(db, row.get("client_id"), uid)
    return _row_to_detail(row, client_nom)


# ── POST /documents/{id}/create-acompte ─────────────────────────────────────
# Facture d'acompte séparée (Batch 12 T4-1), distincte du champ Devis.acompte
# (qui n'est qu'une ligne de déduction affichée sur le MÊME document). Ici on
# crée un document facture à part, avec son propre numéro légal futur, une
# seule ligne de synthèse et sa propre TVA — au taux moyen pondéré du devis
# source pour rester correct même si le devis mélange plusieurs taux de TVA.

def _build_acompte_devis(devis: Devis, pourcentage: float, numero_devis_fallback: str | None) -> Devis:
    """Construit le Devis à une seule ligne d'une facture d'acompte.
    Fonction pure — testée directement sans base de données (même pattern que
    `_is_signable` dans public.py)."""
    total_ht = devis.totaux.total_ht
    montant_ht = round(total_ht * pourcentage / 100, 2)
    tva_taux = round(devis.totaux.total_tva / total_ht * 100, 2) if total_ht > 0 else 0.0
    montant_tva = round(montant_ht * tva_taux / 100, 2)
    montant_ttc = round(montant_ht + montant_tva, 2)

    numero_devis = devis.numero_document or numero_devis_fallback or "en cours"
    pct_label = f"{pourcentage:g}"

    return devis.model_copy(update={
        "lignes": [LigneDevis(
            poste="Acompte",
            description=f"Acompte de {pct_label} % sur devis n° {numero_devis}",
            quantite=1,
            unite="forfait",
            prix_unitaire_ht=montant_ht,
            tva_taux=tva_taux,
            source_prix=SourcePrix.ESTIMATION,
        )],
        "totaux": TotauxDevis(total_ht=montant_ht, total_tva=montant_tva, total_ttc=montant_ttc),
        "type_facture": "acompte",
        "numero_document": None,
        "acompte": None,
        "notes": None,
    })


@router.post("/{doc_id}/create-acompte", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
def create_acompte(
    doc_id: str,
    body: CreateAcompteRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = current_user.user_id
    db = get_supabase_admin()

    source = _fetch_source_document(db, doc_id, uid)
    if source["type_doc"] != "devis":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Seul un devis peut générer une facture d'acompte")
    if source["statut"] != "signé":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Le devis doit être signé avant de générer une facture d'acompte")

    devis = Devis(**source["devis_payload"])
    acompte_devis = _build_acompte_devis(devis, body.pourcentage, source.get("numero"))

    titre_source = source.get("titre") or devis.client.nom or ""
    titre = f"Facture d'acompte {body.pourcentage:g}% - {titre_source}".strip(" -")

    try:
        ins = db.table("documents").insert({
            "user_id": uid,
            "client_id": source.get("client_id"),
            "type_doc": "facture",
            "titre": titre,
            "numero_document": None,
            "date_document": datetime.now(timezone.utc).date().isoformat(),
            "devis_payload": acompte_devis.model_dump(),
            "total_ttc": acompte_devis.totaux.total_ttc,
            "statut": "brouillon",
            "document_source_id": doc_id,
        }).execute()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    row = ins.data[0]
    client_nom = _client_nom_for(db, row.get("client_id"), uid)
    return _row_to_detail(row, client_nom)


# ── PATCH /documents/{id} + POST /documents/{id}/send ───────────────────────

# Statut → colonne date à horodater à la transition (idempotent : jamais écrasée)
STATUT_DATE_COLUMN: dict[str, str] = {
    "envoyé": "date_envoi",
    "signé": "date_signature",
    "payé": "date_paiement",
    "refusé": "date_refus",
    "expiré": "date_expiration",
}


def _statut_transition_update(uid: str, doc: dict, nouveau_statut: str) -> dict:
    """
    Construit le dict de mise à jour pour une transition de statut :
    horodatage idempotent (une date déjà renseignée n'est jamais écrasée) +
    attribution du numéro légal séquentiel à la première transition brouillon→envoyé.
    Partagé par PATCH /documents/{id} et POST /documents/{id}/send — ne jamais
    dupliquer cette logique, l'attribution du numéro ne doit se faire qu'une fois.
    """
    update_data: dict = {"statut": nouveau_statut}

    date_col = STATUT_DATE_COLUMN.get(nouveau_statut)
    if date_col and not doc.get(date_col):
        update_data[date_col] = datetime.now(timezone.utc).isoformat()

    if (
        nouveau_statut == "envoyé"
        and doc["statut"] == "brouillon"
        and not doc.get("numero")
    ):
        type_rpc = "facture" if doc["type_doc"] == "facture" else "devis"
        numero = get_next_numero(uid, type_rpc)
        logger.info("[STATUT] numéro attribué par RPC : %r", numero)
        update_data["numero"] = numero

    return update_data


@router.patch("/{doc_id}", response_model=StatusPatchResponse)
def patch_document_status(
    doc_id: str,
    update: StatusUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = current_user.user_id
    db = get_supabase_admin()

    try:
        existing = (
            db.table("documents")
            .select("statut, numero, type_doc, date_envoi, date_signature, date_paiement, date_refus, date_expiration")
            .eq("id", doc_id)
            .eq("user_id", uid)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    logger.info(
        "[PATCH] doc_id=%s uid=%s statut_reçu=%r lignes_trouvées=%d",
        doc_id, uid, update.statut, len(existing.data) if existing.data else 0,
    )

    if not existing.data:
        logger.warning("[PATCH] 404 — document introuvable pour doc_id=%s uid=%s", doc_id, uid)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")

    doc = existing.data[0]
    update_data = _statut_transition_update(uid, doc, update.statut)

    try:
        db.table("documents").update(update_data).eq("id", doc_id).eq("user_id", uid).execute()
    except Exception as exc:
        logger.error(
            "[PATCH] ÉCHEC UPDATE documents — doc_id=%s update_data=%r erreur=%s",
            doc_id, update_data, exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Mise à jour échouée : {exc}",
        )

    return StatusPatchResponse(
        statut=update.statut,
        numero=update_data.get("numero", doc["numero"]),
    )


# ── DELETE /documents/{id} ───────────────────────────────────────────────────
# Soft delete uniquement : deleted_at = now(). Jamais de suppression physique.
# Batch 14 : autorisé pour n'importe quel statut (plus de restriction brouillon/
# refusé) — le soft delete ne fait déjà que masquer la ligne des listes/dashboard,
# elle reste en base avec son numéro légal intact (jamais réattribuable grâce à
# la contrainte UNIQUE (user_id, type_doc, numero) — Batch 13 T2), donc la
# traçabilité fiscale n'est jamais compromise même en supprimant un document
# envoyé/signé/payé.

@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: str, current_user: CurrentUser = Depends(get_current_user)):
    uid = current_user.user_id
    db = get_supabase_admin()

    try:
        existing = (
            db.table("documents")
            .select("statut")
            .eq("id", doc_id)
            .eq("user_id", uid)
            .is_("deleted_at", "null")
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    if not existing.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")

    try:
        db.table("documents").update(
            {"deleted_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", doc_id).eq("user_id", uid).execute()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ── POST /documents/{id}/send ────────────────────────────────────────────────
# Génère le PDF, l'archive dans Supabase Storage (best-effort), l'envoie par
# email via Resend, puis déclenche la transition brouillon→envoyé (numéro légal
# attribué via _statut_transition_update — jamais dupliqué).
#
# Ordre volontaire : l'email doit réussir AVANT toute écriture en base. Un
# échec d'envoi ne doit jamais laisser un document marqué "envoyé" à tort, ni
# gaspiller un numéro légal séquentiel.

@router.post("/{doc_id}/send", response_model=SendEmailResponse)
def send_document_email(
    doc_id: str,
    body: SendEmailRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = current_user.user_id
    db = get_supabase_admin()

    try:
        existing = (
            db.table("documents")
            .select("*")
            .eq("id", doc_id)
            .eq("user_id", uid)
            .is_("deleted_at", "null")
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    if not existing.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")

    doc = existing.data[0]

    try:
        devis = Devis(**doc["devis_payload"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Devis invalide : {exc}")

    # ⚠️ with_tva n'est pas stocké en base (c'est un simple toggle d'affichage
    # côté frontend, jamais persisté). On le déduit du total_tva du devis déjà
    # calculé : 0 = le devis a été généré/exporté en mode "sans TVA".
    # cf. piège documenté dans CLAUDE.md.
    with_tva = (devis.totaux.total_tva or 0) > 0

    try:
        pdf_bytes = generate_quote_pdf(devis, doc["type_doc"], with_tva, doc.get("date_document"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Génération PDF échouée : {exc}")

    label = "Facture" if doc["type_doc"] == "facture" else "Devis"
    numero_affiche = doc.get("numero_document") or doc.get("numero") or ""
    artisan_nom = devis.artisan.nom or ""
    subject = f"{label} {numero_affiche} — {artisan_nom}".strip(" —")
    default_message = (
        f"Bonjour,<br><br>Veuillez trouver ci-joint votre {label.lower()} "
        f"{numero_affiche}.<br><br>Cordialement,<br>{artisan_nom}"
    )
    html_body = body.message.replace("\n", "<br>") if body.message else default_message
    filename = f"{doc.get('titre') or label}.pdf"

    # Étape critique : si l'envoi échoue, send_devis_email lève une HTTPException
    # et on s'arrête ici — rien n'est écrit en base, aucun numéro n'est attribué.
    send_devis_email(
        to=body.email_destinataire,
        subject=subject,
        html_body=html_body,
        pdf_bytes=pdf_bytes,
        pdf_filename=filename,
    )

    # Archivage best-effort — ne doit jamais faire échouer une requête dont
    # l'email a déjà été envoyé avec succès.
    archive_document_pdf(uid, doc_id, pdf_bytes)

    update_data = _statut_transition_update(uid, doc, "envoyé")
    update_data["date_email_envoye"] = datetime.now(timezone.utc).isoformat()
    update_data["email_destinataire"] = body.email_destinataire

    try:
        db.table("documents").update(update_data).eq("id", doc_id).eq("user_id", uid).execute()
    except Exception as exc:
        logger.error(
            "[SEND] email envoyé mais échec de la mise à jour du document — doc_id=%s erreur=%s",
            doc_id, exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email envoyé mais mise à jour du document échouée : {exc}",
        )

    return SendEmailResponse(
        statut="envoyé",
        numero=update_data.get("numero", doc.get("numero")),
        date_email_envoye=update_data["date_email_envoye"],
    )


# ── GET /documents/{id}/signature-link ───────────────────────────────────────
# Génère (si absent) puis renvoie le lien public de signature électronique
# (Batch 12 T3). Uniquement pour un devis envoyé — pas de sens à faire signer
# une facture, un brouillon, ou un devis déjà clôturé (signé/refusé/expiré/payé).
# Le token est généré à la demande (pas à la transition brouillon→envoyé) pour
# couvrir aussi bien les nouveaux devis que ceux déjà envoyés avant cette
# fonctionnalité.

SIGNATURE_TOKEN_VALIDITE_JOURS = 90  # plafond de sécurité indépendant de validite_jours


@router.get("/{doc_id}/signature-link")
def get_signature_link(doc_id: str, current_user: CurrentUser = Depends(get_current_user)):
    uid = current_user.user_id
    db = get_supabase_admin()

    try:
        existing = (
            db.table("documents")
            .select("type_doc, statut, signature_token, signature_token_expires_at")
            .eq("id", doc_id)
            .eq("user_id", uid)
            .is_("deleted_at", "null")
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    if not existing.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")

    doc = existing.data[0]
    if doc["type_doc"] != "devis":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Seul un devis peut être signé électroniquement")
    if doc["statut"] != "envoyé":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Le lien de signature n'est disponible que pour un devis au statut 'envoyé'",
        )

    token = doc.get("signature_token")
    if not token:
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.now(timezone.utc) + timedelta(days=SIGNATURE_TOKEN_VALIDITE_JOURS)).isoformat()
        try:
            db.table("documents").update({
                "signature_token": token,
                "signature_token_expires_at": expires_at,
            }).eq("id", doc_id).eq("user_id", uid).execute()
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    settings = get_settings()
    return {"url": f"{settings.frontend_url}/devis/{token}"}
