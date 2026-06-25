"""Endpoints choroplèthe : FeatureCollections GeoJSON prix/m² par maille."""

import asyncpg
from fastapi import APIRouter, Depends, Query, Response

from ..config import settings
from ..db import get_connection
from ..queries import (
    Lod,
    TypeLocal,
    communes_query,
    departements_query,
)

router = APIRouter(prefix="/api/v1/choropleth", tags=["choropleth"])

GEOJSON_MEDIA_TYPE = "application/geo+json"


def _geojson_response(payload: str) -> Response:
    """Renvoie le GeoJSON déjà sérialisé par PostgreSQL, avec cache HTTP."""
    return Response(
        content=payload,
        media_type=GEOJSON_MEDIA_TYPE,
        headers={"Cache-Control": f"public, max-age={settings.cache_max_age}"},
    )


@router.get("/communes")
async def choropleth_communes(
    type_local: TypeLocal = Query(TypeLocal.appartement),
    lod: Lod = Query(Lod.mid),
    code_departement: str | None = Query(
        None, min_length=2, max_length=3, pattern=r"^[0-9AB]{2,3}$"
    ),
    conn: asyncpg.Connection = Depends(get_connection),
) -> Response:
    """Choroplèthe communal du prix/m² médian (filtrable par département)."""
    payload = await conn.fetchval(
        communes_query(lod), type_local.value, code_departement
    )
    return _geojson_response(payload)


@router.get("/departements")
async def choropleth_departements(
    type_local: TypeLocal = Query(TypeLocal.appartement),
    lod: Lod = Query(Lod.low),
    conn: asyncpg.Connection = Depends(get_connection),
) -> Response:
    """Choroplèthe départemental du prix/m² médian (vue dézoomée)."""
    payload = await conn.fetchval(departements_query(lod), type_local.value)
    return _geojson_response(payload)
