# tests/integration/test_health.py
import pytest


@pytest.mark.integration
class TestHealth:
    def test_health_ok(self, client):
        """Smoke test — l'API doit répondre status=ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["db"] == "sqlite"
        assert "version" in data

    def test_root_accessible(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_docs_swagger_accessible(self, client):
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_json_accessible(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "ShopFlow API"
