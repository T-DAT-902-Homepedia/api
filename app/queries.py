"""Requêtes SQL read-only construisant des FeatureCollections GeoJSON.

La sérialisation GeoJSON est faite par PostgreSQL (json_build_object / ST_AsGeoJSON)
pour éviter tout travail lourd côté Python. Le niveau de détail (LOD) sélectionne
une colonne géométrie via un mapping sûr (jamais d'interpolation de paramètre client).
"""

from enum import StrEnum

# Mapping LOD -> nom de colonne littéral (validé, non issu d'une entrée brute).
_GEOM_COLUMN = {"low": "geom_low", "mid": "geom_mid", "high": "geom_high"}


class Lod(StrEnum):
    low = "low"
    mid = "mid"
    high = "high"


class TypeLocal(StrEnum):
    maison = "Maison"
    appartement = "Appartement"


def communes_query(lod: Lod) -> str:
    """FeatureCollection des communes pour un type de bien, dépt optionnel.

    Params : $1 = type_local, $2 = code_departement (NULL = toutes).
    """
    geom = _GEOM_COLUMN[lod.value]
    return f"""
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', coalesce(json_agg(json_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(g.{geom})::json,
                'properties', json_build_object(
                    'code_commune', g.code_commune,
                    'nom', g.nom_commune,
                    'code_departement', g.code_departement,
                    'prix_m2_median', a.prix_m2_median,
                    'prix_m2_p25', a.prix_m2_p25,
                    'prix_m2_p75', a.prix_m2_p75,
                    'nb_transactions', a.nb_transactions,
                    'fiable', a.fiable
                )
            )), '[]'::json)
        )
        FROM commune_geometry g
        JOIN agg_commune a USING (code_commune)
        WHERE a.type_local = $1
          AND ($2::text IS NULL OR g.code_departement = $2)
    """  # noqa: S608 — {geom} provient d'un mapping interne, pas du client


def departements_query(lod: Lod) -> str:
    """FeatureCollection des départements pour un type de bien.

    Param : $1 = type_local.
    """
    geom = _GEOM_COLUMN[lod.value]
    return f"""
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', coalesce(json_agg(json_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(g.{geom})::json,
                'properties', json_build_object(
                    'code_departement', g.code_departement,
                    'nom', g.nom,
                    'prix_m2_median', a.prix_m2_median,
                    'prix_m2_p25', a.prix_m2_p25,
                    'prix_m2_p75', a.prix_m2_p75,
                    'nb_transactions', a.nb_transactions,
                    'fiable', a.fiable
                )
            )), '[]'::json)
        )
        FROM departement_geometry g
        JOIN agg_departement a USING (code_departement)
        WHERE a.type_local = $1
    """  # noqa: S608 — {geom} provient d'un mapping interne, pas du client
