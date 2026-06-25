"""Tests de surface des endpoints choroplèthe.

Sans PostGIS, on ne peut pas exercer les requêtes ; on vérifie que les routes
sont bien montées et que le schéma OpenAPI expose les paramètres attendus.
"""


def test_choropleth_routes_registered(client):
    schema = client._transport.app.openapi()
    paths = schema["paths"]
    assert "/api/v1/choropleth/communes" in paths
    assert "/api/v1/choropleth/departements" in paths


def test_communes_params_documented(client):
    schema = client._transport.app.openapi()
    params = {
        p["name"]
        for p in schema["paths"]["/api/v1/choropleth/communes"]["get"]["parameters"]
    }
    assert {"type_local", "lod", "code_departement"} <= params
