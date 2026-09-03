from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status

from app.core.supabase_client import get_supabase_admin


def get_next_numero(user_id: str, type_doc: str) -> str:
    """
    Appelle la RPC Postgres get_next_numero — atomique, reset annuel inclus.
    type_doc : 'devis' | 'facture'
    Retourne ex. 'DEV-2026-001' ou 'FAC-2026-001'.
    """
    try:
        result = (
            get_supabase_admin()
            .rpc("get_next_numero", {"p_user_id": user_id, "p_type": type_doc})
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur numérotation : {exc}",
        )

    data = result.data
    # supabase-py peut retourner le scalaire text directement (str) ou enveloppé
    # dans une liste / dict selon la version de PostgREST — on normalise ici.
    if isinstance(data, list):
        if not data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="RPC get_next_numero : liste vide inattendue",
            )
        item = data[0]
        data = next(iter(item.values())) if isinstance(item, dict) else item

    if not isinstance(data, str) or not data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RPC get_next_numero : réponse inattendue (type={type(data).__name__!r}, valeur={data!r})",
        )
    return data


# ── Aperçu du prochain numéro (Batch 13 T2) ──────────────────────────────
# ⚠️ Lecture seule, jamais d'écriture ni d'incrément — uniquement pour
# l'affichage "Prochain devis : ..." dans le formulaire. Le numéro LÉGAL
# définitif reste attribué exclusivement par get_next_numero() ci-dessus
# (RPC atomique). Dupliquer ici la logique de calcul en pur Python est sans
# risque de race condition puisque rien n'est jamais écrit — mais reste une
# duplication à tenir manuellement synchronisée avec la fonction Postgres
# get_next_numero (cf. migration_batch13_t2_numerotation.sql) si le format
# ou la règle de reset changent un jour.

def format_numero(compteur: int, prefixe: str, inclure_annee: bool, padding: int, annee: int) -> str:
    """Formate un numéro de document — pure, testable, reflète EXACTEMENT
    la formule appliquée dans la fonction Postgres get_next_numero."""
    annee_part = f"{annee}-" if inclure_annee else ""
    return f"{prefixe}{annee_part}{str(compteur).zfill(padding)}"


def compute_next_compteur(
    compteur_actuel: Optional[int],
    compteur_annee: Optional[int],
    numero_debut: int,
    reset_annuel: bool,
    annee_courante: int,
) -> int:
    """Détermine la valeur du PROCHAIN compteur — reflète EXACTEMENT le CASE
    de la fonction Postgres get_next_numero (premier appel jamais fait →
    numero_debut ; reset annuel actif et changement d'année → numero_debut ;
    sinon → compteur_actuel + 1)."""
    if compteur_annee is None:
        return numero_debut
    if reset_annuel and compteur_annee != annee_courante:
        return numero_debut
    return (compteur_actuel or 0) + 1


# Colonnes DB par type — "devis" et "factures" ne se pluralisent pas pareil
# (compteur_devis / compteur_factures), d'où cette table plutôt qu'une
# interpolation de chaîne fragile.
_COLONNES_PAR_TYPE = {
    "devis": {
        "compteur": "compteur_devis",
        "compteur_annee": "compteur_devis_annee",
        "numero_debut": "devis_numero_debut",
        "prefixe": "devis_numero_prefixe",
        "inclure_annee": "devis_numero_inclure_annee",
        "padding": "devis_numero_padding",
    },
    "facture": {
        "compteur": "compteur_factures",
        "compteur_annee": "compteur_factures_annee",
        "numero_debut": "facture_numero_debut",
        "prefixe": "facture_numero_prefixe",
        "inclure_annee": "facture_numero_inclure_annee",
        "padding": "facture_numero_padding",
    },
}


def preview_next_compteur(user_id: str, type_doc: str) -> int:
    """Valeur brute (non formatée) du prochain compteur — lecture seule,
    jamais d'écriture. Base du champ `..._prochain_compteur` exposé par
    GET /profile/numerotation-status, pour permettre au frontend de
    reformater localement l'aperçu en direct (prefixe/année/padding) sans
    round-trip serveur à chaque frappe."""
    cols = _COLONNES_PAR_TYPE["devis" if type_doc == "devis" else "facture"]
    db = get_supabase_admin()
    try:
        result = (
            db.table("entreprises")
            .select(f"{cols['compteur']}, {cols['compteur_annee']}, {cols['numero_debut']}, numero_reset_annuel")
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil introuvable")

    row = result.data[0]
    return compute_next_compteur(
        compteur_actuel=row.get(cols["compteur"]),
        compteur_annee=row.get(cols["compteur_annee"]),
        numero_debut=row[cols["numero_debut"]],
        reset_annuel=row["numero_reset_annuel"],
        annee_courante=datetime.now(timezone.utc).year,
    )
