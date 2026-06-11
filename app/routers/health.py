"""Endpoint de santé."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict:
    """Vérifie que l'API répond."""
    return {"status": "ok"}
