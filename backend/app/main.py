"""
Point d'entrée FastAPI.
Configure CORS, inclut tous les routers, expose la doc Swagger.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import quotes, pdf, word

settings = get_settings()

app = FastAPI(
    title="BTP SaaS API",
    description="API de génération de devis IA pour artisans et PME du BTP",
    version="1.0.0",
    docs_url="/docs",       # Swagger UI : http://localhost:8000/docs
    redoc_url="/redoc",     # ReDoc : http://localhost:8000/redoc
)

# ── CORS ────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────────
app.include_router(quotes.router)
app.include_router(pdf.router)
app.include_router(word.router)


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
