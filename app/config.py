from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"
    sec_user_agent: str = "SEC8KMonitor contact@example.com"
    database_url: str = "sqlite:///./sec8k.db"
    refresh_interval_hours: int = 3
    admin_token: str = "change-me"
    cron_secret: str = ""

    @field_validator("refresh_interval_hours", mode="before")
    @classmethod
    def _coerce_empty_int(cls, v: object) -> object:
        return v if v != "" else 3


settings = Settings()
