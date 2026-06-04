from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../../.env", ".env"), env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(default="postgresql+asyncpg://operator:operator_dev_password@postgres:5432/operator")
    redis_url: str = Field(default="redis://redis:6379/0")
    backend_cors_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")
    jwt_secret_key: str = Field(default="replace-with-a-long-random-secret")
    jwt_access_token_minutes: int = Field(default=15)
    jwt_refresh_token_days: int = Field(default=30)
    ollama_base_url: str = Field(default="http://ollama-service:11434")
    ollama_model: str = Field(default="llama3")
    openai_api_key: str | None = Field(default=None)
    openai_model: str = Field(default="gpt-5.5")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
