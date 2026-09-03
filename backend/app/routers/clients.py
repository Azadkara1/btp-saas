"""
Routeur clients — Phase 4.

GET  /clients          → liste des clients (nb documents + CA total, agrégés en Python
                          comme list_documents dans documents.py — pas de RPC nécessaire
                          à ce volume de données)
GET  /clients/{id}     → fiche client + historique de ses documents
PUT  /clients/{id}     → édition des coordonnées

⚠️  Client service_role : filtrage user_id obligatoire sur chaque requête.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user, CurrentUser
from app.core.supabase_client import get_supabase_admin
from app.models.client import ClientSummary, ClientDetail, ClientUpdate
from app.models.document import DocumentSummary

router = APIRouter()


# ── GET /clients ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[ClientSummary])
def list_clients(current_user: CurrentUser = Depends(get_current_user)):
    uid = current_user.user_id
    db = get_supabase_admin()

    try:
        clients_res = (
            db.table("clients")
            .select("id, nom, adresse, code_postal, ville")
            .eq("user_id", uid)
            .order("nom")
            .execute()
        )
        docs_res = (
            db.table("documents")
            .select("client_id, total_ttc")
            .eq("user_id", uid)
            .is_("deleted_at", "null")
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    clients = clients_res.data or []
    docs = docs_res.data or []

    # Agrégation nb_documents + CA total par client_id
    nb_map: dict[str, int] = {}
    ca_map: dict[str, float] = {}
    for d in docs:
        cid = d.get("client_id")
        if not cid:
            continue
        nb_map[cid] = nb_map.get(cid, 0) + 1
        ca_map[cid] = ca_map.get(cid, 0.0) + float(d["total_ttc"] or 0)

    return [
        ClientSummary(
            id=c["id"],
            nom=c["nom"],
            adresse=c.get("adresse"),
            code_postal=c.get("code_postal"),
            ville=c.get("ville"),
            nb_documents=nb_map.get(c["id"], 0),
            ca_total=round(ca_map.get(c["id"], 0.0), 2),
        )
        for c in clients
    ]


# ── GET /clients/{id} ────────────────────────────────────────────────────────

@router.get("/{client_id}", response_model=ClientDetail)
def get_client(client_id: str, current_user: CurrentUser = Depends(get_current_user)):
    uid = current_user.user_id
    db = get_supabase_admin()

    try:
        c_res = (
            db.table("clients")
            .select("id, nom, adresse, code_postal, ville")
            .eq("id", client_id)
            .eq("user_id", uid)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    if not c_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client introuvable")

    client = c_res.data[0]

    try:
        docs_res = (
            db.table("documents")
            .select(
                "id, type_doc, titre, numero, numero_document, total_ttc, "
                "statut, date_document, created_at, document_source_id, "
                "date_envoi, date_signature, date_paiement, date_refus, date_expiration, "
                "date_email_envoye, email_destinataire, signature_nom_signataire"
            )
            .eq("client_id", client_id)
            .eq("user_id", uid)
            .is_("deleted_at", "null")
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    docs = docs_res.data or []
    documents = [
        DocumentSummary(
            id=d["id"],
            type_doc=d["type_doc"],
            titre=d.get("titre"),
            numero=d.get("numero"),
            numero_document=d.get("numero_document"),
            client_nom=client["nom"],
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

    return ClientDetail(
        id=client["id"],
        nom=client["nom"],
        adresse=client.get("adresse"),
        code_postal=client.get("code_postal"),
        ville=client.get("ville"),
        nb_documents=len(documents),
        ca_total=round(sum(d.total_ttc or 0 for d in documents), 2),
        documents=documents,
    )


# ── PUT /clients/{id} ────────────────────────────────────────────────────────

@router.put("/{client_id}", response_model=ClientSummary)
def update_client(
    client_id: str,
    update: ClientUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = current_user.user_id
    db = get_supabase_admin()

    try:
        existing = (
            db.table("clients")
            .select("id")
            .eq("id", client_id)
            .eq("user_id", uid)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    if not existing.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client introuvable")

    update_data = update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aucune donnée à mettre à jour")

    try:
        db.table("clients").update(update_data).eq("id", client_id).eq("user_id", uid).execute()
        c_res = (
            db.table("clients")
            .select("id, nom, adresse, code_postal, ville")
            .eq("id", client_id)
            .eq("user_id", uid)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    client = c_res.data[0]

    try:
        docs_res = (
            db.table("documents")
            .select("total_ttc")
            .eq("client_id", client_id)
            .eq("user_id", uid)
            .is_("deleted_at", "null")
            .execute()
        )
        docs = docs_res.data or []
    except Exception:
        docs = []

    return ClientSummary(
        id=client["id"],
        nom=client["nom"],
        adresse=client.get("adresse"),
        code_postal=client.get("code_postal"),
        ville=client.get("ville"),
        nb_documents=len(docs),
        ca_total=round(sum(float(d["total_ttc"] or 0) for d in docs), 2),
    )
