"""App configuration, read from environment variables (or a local .env file).

Nothing about a specific server lives here: every value comes from the
environment. See .env.example for the full list.
"""
from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",          # used when present (local development)
        env_file_encoding="utf-8",
        extra="ignore",           # .env may hold Docker-only values too
    )

    db_host: str
    db_port: int = 3306
    db_name: str
    db_user: str
    db_password: SecretStr        # SecretStr: printed as '**********', never in clear

    @property
    def database_url(self) -> URL:
        """Connection address for SQLAlchemy, built from the parts above."""
        return URL.create(
            "mysql+pymysql",
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"charset": "utf8mb4"},
        )


@lru_cache
def get_settings() -> Settings:
    """Load settings once and reuse them."""
    return Settings()
