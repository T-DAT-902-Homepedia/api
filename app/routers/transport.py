"""Endpoints transport : géométrie communale + densité d'arrêts par commune.

La géométrie (lourde, statique) et les valeurs (légères, densité d'arrêts) sont
servies séparément : le front charge la géométrie une fois et ne recharge que les
valeurs. Données issues du silver duckpipe `transport_commune`.
"""

import asyncpg
from fastapi import APIRouter, Depends, Query, Response

from ..db import get_connection
from ..queries import (
    Lod,
    transport_geometry_query,
    transport_values_query,
)

router = APIRouter(prefix="/api/v1/transport", tags=["transport"])

GEOJSON_MEDIA_TYPE = "application/geo+json"


# Géométrie : contours communaux stables mais pas immuables (corrections de
# périmètre, MAJ du référentiel) -> cache 1 h (assez pour ne pas re-télécharger
# les ~10 Mo en boucle, assez court pour propager un correctif).
# Valeurs : recalculées à chaque run du pipeline -> cache court (5 min).
_GEOMETRY_CACHE = "public, max-age=3600"
_VALUES_CACHE = "public, max-age=300"


def _geojson_response(payload: str, cache: str) -> Response:
    """GeoJSON déjà sérialisé par PostgreSQL, avec cache HTTP."""
    return Response(
        content=payload,
        media_type=GEOJSON_MEDIA_TYPE,
        headers={"Cache-Control": cache},
    )


def _json_response(payload: str, cache: str) -> Response:
    """JSON déjà sérialisé par PostgreSQL, avec cache HTTP."""
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Cache-Control": cache},
    )


@router.get("/communes/geometry")
async def transport_geometry(
    lod: Lod = Query(Lod.mid),
    code_departement: str | None = Query(
        None, min_length=2, max_length=3, pattern=r"^[0-9AB]{2,3}$"
    ),
    conn: asyncpg.Connection = Depends(get_connection),
) -> Response:
    """Contours communaux seuls (statiques, fortement cachés)."""
    payload = await conn.fetchval(transport_geometry_query(lod), code_departement)
    return _geojson_response(payload, _GEOMETRY_CACHE)


@router.get("/communes/values")
async def transport_values(
    code_departement: str | None = Query(
        None, min_length=2, max_length=3, pattern=r"^[0-9AB]{2,3}$"
    ),
    conn: asyncpg.Connection = Depends(get_connection),
) -> Response:
    """Densité d'arrêts (nb_arrets / densite_arrets_km2) par commune."""
    payload = await conn.fetchval(transport_values_query(), code_departement)
    return _json_response(payload, _VALUES_CACHE)
