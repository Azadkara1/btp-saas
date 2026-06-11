"""
Router FastAPI pour l'export PDF.
Route principale : POST /pdf/export
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from app.models.pdf import PdfRequest
from app.services.pdf_service import generate_quote_pdf

router = APIRouter(prefix="/pdf", tags=["PDF"])


@router.post("/export")
async def export_pdf(request: PdfRequest):
    """
    Génère et retourne un PDF du devis.
    Le fichier est retourné directement en bytes (application/pdf).
    """
    try:
        pdf_bytes = generate_quote_pdf(request.devis, request.document_type, request.with_tva, request.document_date)
        filename = f"{request.document_type}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur génération PDF : {str(e)}")
