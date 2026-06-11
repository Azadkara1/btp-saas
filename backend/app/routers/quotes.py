"""
Router FastAPI pour la génération de devis.
Route principale : POST /quotes/generate
"""
from fastapi import APIRouter, HTTPException
from app.models.quote import QuoteRequest, QuoteResponse
from app.services.claude_service import generate_quote

router = APIRouter(prefix="/quotes", tags=["Devis"])


@router.post("/generate", response_model=QuoteResponse)
async def generate_quote_endpoint(request: QuoteRequest):
    """
    Génère un devis professionnel à partir d'une description textuelle.
    
    - Analyse la description via Claude Sonnet
    - Recherche les prix manquants via Tool Use
    - Retourne un devis JSON structuré et validé
    """
    if not request.description.strip():
        raise HTTPException(status_code=400, detail="La description du chantier est obligatoire.")

    result = await generate_quote(request)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return result


@router.get("/health")
async def health_check():
    """Vérifie que le service de génération de devis est opérationnel."""
    return {"status": "ok", "service": "quotes"}
