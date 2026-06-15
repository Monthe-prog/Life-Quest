from __future__ import annotations

from typing import Protocol

from app.modules.oracle.service import OracleResult, oracle_service


class OracleClient(Protocol):
    @property
    def configured(self) -> bool: ...

    @property
    def model_name(self) -> str: ...

    async def generate(self, prompt: str, instructions: str | None = None) -> OracleResult: ...

    async def breakdown_goal(self, title: str, horizon: str, child_horizon: str) -> OracleResult: ...

    def parse_tasks(self, text: str, parent_title: str) -> list[str]: ...


def get_oracle_client() -> OracleClient:
    return oracle_service
