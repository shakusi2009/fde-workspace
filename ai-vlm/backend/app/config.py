from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "Stephen AI VLM Service"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/vlm"

    volcengine_rds_engine: str = "mysql"
    volcengine_rds_host: str = ""
    volcengine_rds_port: str = ""
    volcengine_rds_database: str = ""
    volcengine_rds_username: str = ""
    volcengine_rds_password: str = ""
    volcengine_rds_ssl_mode: str = ""
    volcengine_rds_connect_timeout: int = 5

    tos_access_key: str = ""
    tos_secret_key: str = ""

    model_agent_name: str = ""
    model_agent_api_key: str = ""
    model_agent_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def rds_configured(self) -> bool:
        required = (
            self.volcengine_rds_host,
            self.volcengine_rds_port,
            self.volcengine_rds_database,
            self.volcengine_rds_username,
            self.volcengine_rds_password,
        )
        return all(value.strip() for value in required)

    @property
    def rds_engine(self) -> str:
        return self.volcengine_rds_engine.strip().lower() or "mysql"

    @property
    def tos_configured(self) -> bool:
        return bool(self.tos_access_key.strip() and self.tos_secret_key.strip())

    @property
    def model_agent_configured(self) -> bool:
        return bool(
            self.model_agent_api_key.strip()
            and self.model_agent_base_url.strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
