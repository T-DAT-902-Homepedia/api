"""Fixtures de test."""

import os
from collections.abc import AsyncIterator

import httpx
import pytest

# La config exige API_DATABASE_URL ; on fournit un DSN factice avant d'importer
# l'app. Les tests n'ouvrent jamais le pool (lifespan non déclenché par
# ASGITransport), donc aucune vraie connexion n'est tentée.
os.environ.setdefault(
    "API_DATABASE_URL",
    "postgresql://test:test@localhost:5432/test",
)

from app.main import app  # noqa: E402 — doit suivre la mise en place de l'env


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
