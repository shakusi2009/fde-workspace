from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_agent_api_key: str = ""
    model_agent_base_url: str = ""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def model_agent_configured(self) -> bool:
        return bool(
            self.model_agent_api_key.strip()
            and self.model_agent_base_url.strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
