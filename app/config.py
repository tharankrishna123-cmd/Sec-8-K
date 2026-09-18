from __future__ import annotations

from typing import Any

from pydantic import model_validator
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

    @model_validator(mode="before")
    @classmethod
    def _drop_empty_env_vars(cls, data: Any) -> Any:
        # Vercel auto-creates env vars with empty strings for detected field names.
        # Removing them lets Pydantic fall back to the field defaults instead of
        # failing to parse "" as int (refresh_interval_hours) or using a bad URL.
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if v != ""}
        return data


settings = Settings()
