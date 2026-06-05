from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_service_status() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "online", "service": "operator-backend"}


def test_swagger_docs_and_openapi_schema_are_available_under_api_prefix() -> None:
    client = TestClient(app)

    docs_response = client.get("/api/docs")
    schema_response = client.get("/api/openapi.json")

    assert docs_response.status_code == 200
    assert "Swagger UI" in docs_response.text
    assert schema_response.status_code == 200
    assert schema_response.json()["info"]["title"] == "OPERATOR API"


def test_metrics_endpoint_returns_backend_metrics() -> None:
    client = TestClient(app)

    client.get("/health")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "operator_http_requests_total" in response.text
    assert "operator_http_request_duration_seconds" in response.text
