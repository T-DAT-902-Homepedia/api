"""Point d'entrée de l'API read-only Homepedia (DVF)."""

from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .db import create_pool
from .routers import choropleth, health, transport


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await create_pool()
    try:
        yield
    finally:
        await app.state.pool.close()


app = FastAPI(
    title="Homepedia DVF API",
    version="0.1.0",
    summary="API read-only des prix immobiliers au m² (choroplèthe).",
    lifespan=lifespan,
)

# Compression : les FeatureCollections GeoJSON (parfois plusieurs Mo) se
# compressent très bien. minimum_size évite de gzip les petites réponses.
# compresslevel=1 : sur des payloads de dizaines de Mo, le niveau 9 par défaut
# coûte plusieurs secondes de CPU pour ~10 % de taille en moins — mauvais
# compromis. Le niveau 1 divise ce temps par ~4 pour une taille à peine plus grosse.
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=1)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.exception_handler(asyncpg.PostgresError)
async def on_db_error(_: Request, __: asyncpg.PostgresError) -> JSONResponse:
    # Toute erreur PostgreSQL -> 503 sobre, sans fuiter la stack trace au client.
    return JSONResponse(status_code=503, content={"detail": "Database error"})


app.include_router(health.router)
app.include_router(choropleth.router)
app.include_router(transport.router)
