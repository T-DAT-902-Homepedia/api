"""Endpoints transport : géométrie communale, valeurs par mode, et arrêts (points).

La géométrie (lourde, identique pour tous les modes) et les valeurs (légères, par
mode) sont servies séparément : le front charge la géométrie une fois et ne
recharge que les valeurs en changeant de mode.
"""

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from ..db import get_connection
from ..queries import (
    Lod,
    RouteType,
    transport_geometry_query,
    transport_stations_query,
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
    route_type: RouteType = Query(RouteType.all),
    code_departement: str | None = Query(
        None, min_length=2, max_length=3, pattern=r"^[0-9AB]{2,3}$"
    ),
    conn: asyncpg.Connection = Depends(get_connection),
) -> Response:
    """Valeurs (stations / population / densité) par commune pour un mode."""
    payload = await conn.fetchval(
        transport_values_query(), route_type.value, code_departement
    )
    return _json_response(payload, _VALUES_CACHE)


@router.get("/stations")
async def transport_stations(
    bbox: str = Query(..., description="min_lon,min_lat,max_lon,max_lat"),
    route_type: RouteType | None = Query(None),
    conn: asyncpg.Connection = Depends(get_connection),
) -> Response:
    """Points des arrêts individuels dans la bbox (filtrable par mode)."""
    try:
        min_lon, min_lat, max_lon, max_lat = (float(x) for x in bbox.split(","))
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="bbox attendue : min_lon,min_lat,max_lon,max_lat",
        ) from exc
    payload = await conn.fetchval(
        transport_stations_query(),
        min_lon,
        min_lat,
        max_lon,
        max_lat,
        route_type.value if route_type is not None else None,
    )
    return _geojson_response(payload, _VALUES_CACHE)
