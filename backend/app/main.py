"""
Point d'entrée FastAPI.
Configure CORS, inclut tous les routers, expose la doc Swagger.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import quotes, pdf, word
from app.routers.profile import router as profile_router
from app.routers.documents import router as documents_router
from app.routers.clients import router as clients_router
from app.routers.dashboard import router as dashboard_router
from app.routers.public import router as public_router
from app.routers.evenements import router as evenements_router

settings = get_settings()

app = FastAPI(
    title="BTP SaaS API",
    description="API de génération de devis IA pour artisans et PME du BTP",
    version="1.0.0",
    docs_url="/docs",       # Swagger UI : http://localhost:8000/docs
    redoc_url="/redoc",     # ReDoc : http://localhost:8000/redoc
)

# ── CORS ────────────────────────────────────────────────────────
# Configurable via ALLOWED_ORIGIN env var (défaut : localhost:3000)
_origins = (
    ["*"]
    if settings.allowed_origin == "*"
    else [settings.allowed_origin]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
)

# ── Routers ─────────────────────────────────────────────────────
app.include_router(quotes.router)
app.include_router(pdf.router)
app.include_router(word.router)
app.include_router(profile_router, prefix="/profile", tags=["profile"])
app.include_router(documents_router, prefix="/documents", tags=["documents"])
app.include_router(clients_router, prefix="/clients", tags=["clients"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
app.include_router(public_router, prefix="/public", tags=["public"])  # ⚠️ aucune route ici n'est authentifiée
app.include_router(evenements_router, prefix="/evenements", tags=["evenements"])


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
