from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest


REQUEST_COUNT = Counter(
    "operator_http_requests_total",
    "Total HTTP requests handled by the OPERATOR backend.",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "operator_http_request_duration_seconds",
    "HTTP request latency for the OPERATOR backend.",
    ["method", "path"],
)


def normalize_path(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return str(path or request.url.path)


async def metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if request.url.path == "/metrics":
        return await call_next(request)

    method = request.method
    path = normalize_path(request)
    started_at = time.perf_counter()
    status_code = "500"

    try:
        response = await call_next(request)
        status_code = str(response.status_code)
        return response
    finally:
        REQUEST_COUNT.labels(method=method, path=path, status=status_code).inc()
        REQUEST_LATENCY.labels(method=method, path=path).observe(time.perf_counter() - started_at)


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
