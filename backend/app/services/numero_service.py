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
