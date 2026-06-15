from __future__ import annotations

import pytest

from app.modules.oracle.service import OracleService


def test_model_name_reads_current_settings() -> None:
    service = OracleService()
    service.settings.openai_model = "test-oracle-model"

    assert service.model_name == "test-oracle-model"


@pytest.mark.asyncio
async def test_generate_returns_degraded_fallback_when_api_key_is_missing() -> None:
    service = OracleService()
    service.settings.openai_api_key = None

    result = await service.generate("Plan my week")

    assert result.provider == "fallback"
    assert result.degraded is True
    assert result.error == "missing_openai_api_key"
    assert "Oracle channel is degraded" in result.text


def test_extract_text_prefers_output_text() -> None:
    service = OracleService()

    assert service.extract_text({"output_text": "  Mission accepted.  "}) == "Mission accepted."


def test_extract_text_collects_nested_response_text() -> None:
    service = OracleService()
    payload = {
        "output": [
            {"content": [{"text": "First directive."}, {"type": "metadata"}]},
            {"content": [{"text": "Second directive."}]},
        ]
    }

    assert service.extract_text(payload) == "First directive.\nSecond directive."


def test_parse_tasks_limits_and_cleans_numbered_lines() -> None:
    service = OracleService()
    text = """
    1. Define launch scope
    2. Build the first working version
    3. Review progress with evidence
    4. Extra task should not be returned
    """

    assert service.parse_tasks(text, "Launch app") == [
        "Define launch scope",
        "Build the first working version",
        "Review progress with evidence",
    ]


def test_parse_tasks_returns_default_tasks_for_empty_output() -> None:
    service = OracleService()

    tasks = service.parse_tasks("", "Launch app")

    assert len(tasks) == 3
    assert all("Launch app" in task for task in tasks)
