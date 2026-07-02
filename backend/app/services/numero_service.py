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
    return result.data
