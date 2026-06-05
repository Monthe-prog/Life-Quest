from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from app.core.settings import get_settings


ORACLE_INSTRUCTIONS = """
You are the Oracle inside OPERATOR, a cyberpunk life-management RPG.
Speak in a direct, cinematic, mission-control voice.
Be specific, practical, and time-bound. Avoid therapy disclaimers unless safety requires them.
When asked for goal breakdowns, return concise actionable tasks, one per line.
"""


@dataclass
class OracleResult:
    text: str
    provider: str
    degraded: bool = False
    error: str | None = None


class OracleService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def configured(self) -> bool:
        return bool(self.settings.openai_api_key)

    async def generate(self, prompt: str, instructions: str | None = None) -> OracleResult:
        if not self.configured:
            return OracleResult(
                text=self.fallback(prompt),
                provider="fallback",
                degraded=True,
                error="missing_openai_api_key",
            )

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.openai.com/v1/responses",
                    headers={
                        "Authorization": f"Bearer {self.settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.settings.openai_model,
                        "instructions": instructions or ORACLE_INSTRUCTIONS,
                        "input": prompt,
                    },
                )
                response.raise_for_status()
        except httpx.HTTPError:
            return OracleResult(
                text=self.fallback(prompt),
                provider="fallback",
                degraded=True,
                error="openai_request_failed",
            )

        payload = response.json()
        return OracleResult(text=self.extract_text(payload), provider="openai", degraded=False)

    def extract_text(self, payload: dict) -> str:
        if payload.get("output_text"):
            return str(payload["output_text"]).strip()

        parts: list[str] = []
        for item in payload.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if text:
                    parts.append(text)
        return "\n".join(parts).strip() or self.fallback(json.dumps(payload)[:500])

    def fallback(self, prompt: str) -> str:
        return (
            "Operator. Oracle channel is degraded, but the mission remains executable. "
            "Name the objective, define the first visible proof, assign a deadline, and begin."
        )

    async def breakdown_goal(self, title: str, horizon: str, child_horizon: str) -> OracleResult:
        prompt = (
            f"Break this {horizon} goal into exactly three {child_horizon} tasks. "
            f"Goal: {title}. Return only one task per line."
        )
        return await self.generate(prompt)

    def parse_tasks(self, text: str, parent_title: str) -> list[str]:
        tasks = [
            line.strip(" -0123456789.").strip()
            for line in text.splitlines()
            if line.strip()
        ]
        tasks = [task for task in tasks if len(task) >= 4]
        return tasks[:3] or [
            f"Define the first measurable checkpoint for {parent_title}",
            f"Schedule the highest-leverage execution block for {parent_title}",
            f"Report one visible proof of progress toward {parent_title}",
        ]


oracle_service = OracleService()
