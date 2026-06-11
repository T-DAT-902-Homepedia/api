"""Point d'entrée de l'API Homepedia."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import health

app = FastAPI(
    title="Homepedia API",
    version="0.1.0",
    summary="API Homepedia (healthcheck uniquement pour l'instant).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router)
