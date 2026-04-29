from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["docs"] == "/docs"


def test_status_endpoint():
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert "version" in payload["data"]


def test_health_endpoint_without_database_url_does_not_crash():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert "database_details" in payload["data"]
