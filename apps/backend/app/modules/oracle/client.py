from __future__ import annotations

from functools import lru_cache
from typing import Protocol

import httpx

from app.core.settings import get_settings
from app.modules.oracle.service import OracleResult, oracle_service


class OracleClient(Protocol):
    @property
    def configured(self) -> bool: ...

    @property
    def model_name(self) -> str: ...

    async def generate(self, prompt: str, instructions: str | None = None) -> OracleResult: ...

    async def breakdown_goal(self, title: str, horizon: str, child_horizon: str) -> OracleResult: ...

    def parse_tasks(self, text: str, parent_title: str) -> list[str]: ...


class RemoteOracleClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.fallback = oracle_service

    @property
    def configured(self) -> bool:
        return True

    @property
    def model_name(self) -> str:
        return "remote"

    async def generate(self, prompt: str, instructions: str | None = None) -> OracleResult:
        try:
            async with httpx.AsyncClient(timeout=35) as client:
                response = await client.post(
                    f"{self.base_url}/oracle/generate",
                    json={"prompt": prompt, "instructions": instructions},
                )
                response.raise_for_status()
        except httpx.HTTPError:
            return OracleResult(
                text=self.fallback.fallback(prompt),
                provider="fallback",
                degraded=True,
                error="oracle_service_unavailable",
            )

        return self._result_from_payload(response.json())

    async def breakdown_goal(self, title: str, horizon: str, child_horizon: str) -> OracleResult:
        try:
            async with httpx.AsyncClient(timeout=35) as client:
                response = await client.post(
                    f"{self.base_url}/oracle/breakdown-goal",
                    json={"title": title, "horizon": horizon, "child_horizon": child_horizon},
                )
                response.raise_for_status()
        except httpx.HTTPError:
            return OracleResult(
                text=self.fallback.fallback(title),
                provider="fallback",
                degraded=True,
                error="oracle_service_unavailable",
            )

        return self._result_from_payload(response.json())

    def parse_tasks(self, text: str, parent_title: str) -> list[str]:
        return self.fallback.parse_tasks(text, parent_title)

    def _result_from_payload(self, payload: dict[str, object]) -> OracleResult:
        return OracleResult(
            text=str(payload.get("text") or ""),
            provider=str(payload.get("provider") or "remote"),
            degraded=bool(payload.get("degraded")),
            error=str(payload["error"]) if payload.get("error") else None,
        )


@lru_cache
def _remote_oracle_client(base_url: str) -> RemoteOracleClient:
    return RemoteOracleClient(base_url)


def get_oracle_client() -> OracleClient:
    settings = get_settings()
    if settings.oracle_service_url:
        return _remote_oracle_client(settings.oracle_service_url)
    return oracle_service
