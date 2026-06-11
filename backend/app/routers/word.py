"""
Router FastAPI pour l'export Word (.docx).
Route principale : POST /word/export
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from app.models.pdf import PdfRequest
from app.services.word_service import generate_quote_docx

router = APIRouter(prefix="/word", tags=["Word"])


@router.post("/export")
async def export_word(request: PdfRequest):
    """
    Génère et retourne un fichier .docx du devis.
    Permet à l'artisan ou au client de modifier le document dans Word/LibreOffice.
    """
    try:
        docx_bytes = generate_quote_docx(
            request.devis, request.document_type, request.with_tva, request.document_date
        )
        filename = f"{request.document_type}.docx"
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur génération Word : {str(e)}")
