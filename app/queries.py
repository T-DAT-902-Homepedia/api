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


class RouteType(StrEnum):
    all = "ALL"
    bus = "bus"
    tramway = "tramway"
    metro = "métro"
    train = "train"
    autres = "autres"


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


def transport_geometry_query(lod: Lod) -> str:
    """FeatureCollection des contours communaux SANS valeurs (lourd mais statique).

    La géométrie est identique quel que soit le mode de transport : on la sert
    une seule fois (fortement cachée), le front la réutilise pour tous les modes
    et ne recharge que les valeurs légères. Param : $1 = code_departement (NULL = toutes).

    Pour Paris / Lyon / Marseille, `commune_geometry` contient À LA FOIS la commune
    entière (75056 / 69123 / 13055) ET ses arrondissements. On retire le gros
    polygone ville et on garde les arrondissements (rendu plus fin, cohérent avec
    les communes voisines) ; la valeur ville leur est généralisée côté `values`.
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
                    -- Nom de la ville pour les arrondissements PLM : la donnée
                    -- qu'on y généralise est celle de la ville entière.
                    'nom', CASE
                        WHEN g.code_commune BETWEEN '75101' AND '75120' THEN 'Paris'
                        WHEN g.code_commune BETWEEN '69381' AND '69389' THEN 'Lyon'
                        WHEN g.code_commune BETWEEN '13201' AND '13216' THEN 'Marseille'
                        ELSE g.nom_commune
                    END,
                    'code_departement', g.code_departement
                )
            )), '[]'::json)
        )
        FROM commune_geometry g
        WHERE ($1::text IS NULL OR g.code_departement = $1)
          -- Retire les communes entières PLM (on garde leurs arrondissements).
          AND g.code_commune NOT IN ('75056', '69123', '13055')
    """  # noqa: S608 — {geom} provient d'un mapping interne, pas du client


def transport_values_query() -> str:
    """Valeurs par commune pour un mode, en map JSON légère {code_commune: {...}}.

    Payload minuscule (~2 Mo France entière) rechargé à chaque changement de mode,
    fusionné côté front avec la géométrie cachée. Params : $1 = route_type,
    $2 = code_departement (NULL = toutes).

    Clé = code de la géométrie (donc les arrondissements PLM) ; la valeur jointe
    est celle de la commune entière (mapping arrondissement -> ville) : la donnée
    transport est au niveau ville, on la généralise à chaque arrondissement.
    """
    return """
        SELECT coalesce(json_object_agg(g.code_commune, json_build_object(
            'nom', t.nom_commune,
            'nb_stations', t.nb_stations,
            'population', t.population,
            'stations_per_1000hab', t.stations_per_1000hab,
            'stations_per_km2', t.stations_per_km2
        )), '{}'::json)
        FROM commune_geometry g
        JOIN transport_commune t ON t.code_insee = CASE
            WHEN g.code_commune BETWEEN '75101' AND '75120' THEN '75056'
            WHEN g.code_commune BETWEEN '69381' AND '69389' THEN '69123'
            WHEN g.code_commune BETWEEN '13201' AND '13216' THEN '13055'
            ELSE g.code_commune
        END
        WHERE t.route_type = $1
          AND ($2::text IS NULL OR g.code_departement = $2)
          AND g.code_commune NOT IN ('75056', '69123', '13055')
    """


def transport_stations_query() -> str:
    """FeatureCollection des arrêts individuels dans une bbox.

    Params : $1..$4 = min_lon, min_lat, max_lon, max_lat ; $5 = route_type
    (NULL = tous les modes). Le filtre `&&` exploite l'index gist sur geom.
    """
    return """
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', coalesce(json_agg(json_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(s.geom)::json,
                'properties', json_build_object(
                    'station_name', s.station_name,
                    'route_type', s.route_type,
                    'nb_lignes', s.nb_lignes,
                    'code_commune', s.code_commune
                )
            )), '[]'::json)
        )
        FROM transport_stops s
        WHERE s.geom && ST_MakeEnvelope($1, $2, $3, $4, 4326)
          AND ($5::text IS NULL OR s.route_type = $5)
    """
