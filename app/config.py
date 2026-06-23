from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"
    sec_user_agent: str = "SEC8KMonitor contact@example.com"
    database_url: str = "sqlite:///./sec8k.db"
    refresh_interval_hours: int = 3
    admin_token: str = "change-me"


settings = Settings()
