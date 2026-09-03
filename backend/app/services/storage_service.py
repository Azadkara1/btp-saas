"""
Archivage du PDF envoyé dans le bucket Supabase Storage privé "documents-pdf"
(Batch 11 T4) — évite de régénérer le PDF si on doit le re-consulter plus tard.

⚠️ Bucket privé, accédé uniquement via le client service_role (bypass RLS
comme les tables Postgres) : jamais d'accès direct depuis le navigateur.
Chemin : documents-pdf/{user_id}/{document_id}.pdf — namespacé par user_id
même si service_role bypasse déjà les vérifications, en défense en profondeur.
"""
import logging

from app.core.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)

BUCKET = "documents-pdf"


def archive_document_pdf(user_id: str, document_id: str, pdf_bytes: bytes) -> str | None:
    """
    Upload (upsert) le PDF dans le bucket privé. Non bloquant : une erreur
    d'archivage ne doit jamais empêcher l'envoi de l'email déjà réussi.
    Retourne le chemin de stockage, ou None si l'upload a échoué.
    """
    path = f"{user_id}/{document_id}.pdf"
    try:
        get_supabase_admin().storage.from_(BUCKET).upload(
            path,
            pdf_bytes,
            file_options={"content-type": "application/pdf", "upsert": "true"},
        )
        return path
    except Exception as exc:
        logger.warning("[STORAGE] échec archivage PDF (non bloquant) — path=%s erreur=%s", path, exc)
        return None
