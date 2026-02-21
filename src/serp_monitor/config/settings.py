from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    http_timeout: int = Field(default=20, alias="HTTP_TIMEOUT")
    http_retries: int = Field(default=3, alias="HTTP_RETRIES")

    serper_api_key: str = Field(alias="SERPER_API_KEY")
    serper_base_url: str = Field(default="https://google.serper.dev", alias="SERPER_BASE_URL")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
