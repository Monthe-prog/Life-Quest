from __future__ import annotations

import httpx
import pytest

from app.modules.oracle import client as oracle_client
from app.modules.oracle.client import RemoteOracleClient


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self.payload


class FakeAsyncClient:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.requests: list[tuple[str, dict[str, object]]] = []

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
        self.requests.append((url, json))
        return FakeResponse({"text": "Remote directive", "provider": "oracle-service", "degraded": False})


class FailingAsyncClient:
    def __init__(self, *args: object, **kwargs: object) -> None:
        return None

    async def __aenter__(self) -> "FailingAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
        raise httpx.ConnectError("oracle service unavailable")


@pytest.mark.asyncio
async def test_remote_oracle_client_returns_service_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(oracle_client.httpx, "AsyncClient", FakeAsyncClient)
    client = RemoteOracleClient("http://oracle-service:8010/")

    result = await client.generate("Plan my week")

    assert result.text == "Remote directive"
    assert result.provider == "oracle-service"
    assert result.degraded is False


@pytest.mark.asyncio
async def test_remote_oracle_client_degrades_when_service_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(oracle_client.httpx, "AsyncClient", FailingAsyncClient)
    client = RemoteOracleClient("http://oracle-service:8010")

    result = await client.breakdown_goal("Launch product", "monthly", "weekly")

    assert result.provider == "fallback"
    assert result.degraded is True
    assert result.error == "oracle_service_unavailable"
    assert "Oracle channel is degraded" in result.text
