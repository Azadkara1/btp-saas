"""
Routeur documents — Lots 3 & 4.

POST   /documents        → auto-save brouillon post-génération + upsert client
GET    /documents        → historique de l'utilisateur (colonnes indexées)
GET    /documents/{id}   → Devis complet pour réouverture
PATCH  /documents/{id}   → mise à jour statut ; brouillon→envoyé attribue le numéro

⚠️  Client service_role : filtrage user_id obligatoire sur chaque requête.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user, CurrentUser

logger = logging.getLogger(__name__)
from app.core.supabase_client import get_supabase_admin
from app.models.document import (
    DocumentCreate,
    DocumentDetail,
    DocumentSummary,
    StatusUpdate,
    StatusPatchResponse,
)
from app.services.numero_service import get_next_numero

router = APIRouter()


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
    return DocumentDetail(
        id=row["id"],
        type_doc=row["type_doc"],
        titre=row.get("titre"),
        numero=row.get("numero"),
        numero_document=row.get("numero_document"),
        client_nom=body.client_nom,
        total_ttc=float(row["total_ttc"]) if row.get("total_ttc") is not None else None,
        statut=row["statut"],
        date_document=str(row["date_document"]) if row.get("date_document") else None,
        created_at=str(row["created_at"]),
        devis_payload=row["devis_payload"],
    )


# ── GET /documents ───────────────────────────────────────────────────────────

@router.get("", response_model=list[DocumentSummary])
def list_documents(current_user: CurrentUser = Depends(get_current_user)):
    uid = current_user.user_id
    db = get_supabase_admin()

    try:
        docs_res = (
            db.table("documents")
            .select("id, type_doc, titre, numero, numero_document, client_id, total_ttc, statut, date_document, created_at")
            .eq("user_id", uid)
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
        devis_payload=row["devis_payload"],
    )


# ── PATCH /documents/{id} ────────────────────────────────────────────────────

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
            .select("statut, numero, type_doc")
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
    update_data: dict = {"statut": update.statut}

    # Attribution du numéro séquentiel légal à la première transition → "envoyé"
    if (
        update.statut == "envoyé"
        and doc["statut"] == "brouillon"
        and not doc["numero"]
    ):
        type_rpc = "facture" if doc["type_doc"] == "facture" else "devis"
        numero = get_next_numero(uid, type_rpc)
        logger.info("[PATCH] numéro attribué par RPC : %r", numero)
        update_data["numero"] = numero

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
