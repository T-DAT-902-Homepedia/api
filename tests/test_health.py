"""Tests de l'endpoint de santé."""


async def test_healthz_ok(client):
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
