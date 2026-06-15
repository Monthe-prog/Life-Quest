from __future__ import annotations

from fastapi.testclient import TestClient

from app.modules.oracle.service_app import app, oracle_service


def test_oracle_service_health_endpoint_returns_service_status() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "online", "service": "operator-oracle-service"}


def test_oracle_service_generate_degrades_without_api_key() -> None:
    original_api_key = oracle_service.settings.openai_api_key
    oracle_service.settings.openai_api_key = None
    try:
        client = TestClient(app)

        response = client.post("/oracle/generate", json={"prompt": "Plan my week"})
    finally:
        oracle_service.settings.openai_api_key = original_api_key

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "fallback"
    assert payload["degraded"] is True
