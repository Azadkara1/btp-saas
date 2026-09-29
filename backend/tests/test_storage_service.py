"""
Tests de archive_document_pdf() (backend/app/services/storage_service.py) —
jamais couvert jusqu'ici (trouvé par revue de code, Batch 16). Comportement
best-effort volontaire : un échec d'archivage ne doit JAMAIS lever
d'exception (l'email a déjà été envoyé avec succès à ce stade).
"""
from app.services import storage_service


class _FakeStorageBucket:
    def __init__(self, raise_on_upload=False):
        self._raise = raise_on_upload
        self.uploaded = None

    def upload(self, path, pdf_bytes, file_options=None):
        if self._raise:
            raise Exception("bucket introuvable")
        self.uploaded = (path, pdf_bytes, file_options)


class _FakeStorage:
    def __init__(self, bucket):
        self._bucket = bucket

    def from_(self, name):
        assert name == storage_service.BUCKET
        return self._bucket


class _FakeSupabaseClient:
    def __init__(self, bucket):
        self.storage = _FakeStorage(bucket)


def test_archive_document_pdf_succes_retourne_le_chemin(monkeypatch):
    bucket = _FakeStorageBucket()
    monkeypatch.setattr(storage_service, "get_supabase_admin", lambda: _FakeSupabaseClient(bucket))

    path = storage_service.archive_document_pdf("user-1", "doc-1", b"%PDF-1.4")

    assert path == "user-1/doc-1.pdf"
    assert bucket.uploaded[0] == "user-1/doc-1.pdf"
    assert bucket.uploaded[1] == b"%PDF-1.4"


def test_archive_document_pdf_echec_retourne_none_sans_lever(monkeypatch):
    """Le cœur du contrat de cette fonction : jamais d'exception, même si
    l'upload échoue — sinon un email déjà envoyé avec succès ferait quand
    même échouer toute la requête POST /documents/{id}/send."""
    bucket = _FakeStorageBucket(raise_on_upload=True)
    monkeypatch.setattr(storage_service, "get_supabase_admin", lambda: _FakeSupabaseClient(bucket))

    path = storage_service.archive_document_pdf("user-1", "doc-1", b"%PDF-1.4")

    assert path is None
