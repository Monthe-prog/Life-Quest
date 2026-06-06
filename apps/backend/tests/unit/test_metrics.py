from __future__ import annotations

from types import SimpleNamespace

from fastapi import Response

from app.core.metrics import metrics_response, normalize_path


def test_metrics_response_exposes_prometheus_content_type() -> None:
    response = metrics_response()

    assert response.status_code == 200
    assert "text/plain" in response.media_type
    assert b"python_info" in response.body


def test_normalize_path_prefers_route_template() -> None:
    request = SimpleNamespace(scope={"route": SimpleNamespace(path="/api/goals/{goal_id}")}, url=SimpleNamespace(path="/api/goals/123"))

    assert normalize_path(request) == "/api/goals/{goal_id}"


def test_normalize_path_falls_back_to_url_path() -> None:
    request = SimpleNamespace(scope={}, url=SimpleNamespace(path="/health"))

    assert normalize_path(request) == "/health"
