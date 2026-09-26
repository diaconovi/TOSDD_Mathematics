"""Application configuration, loaded from the environment / `.env` file."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Math Job Operator API.

    Example:
        >>> s = Settings(_env_file=None, MONGO_URL="127.0.0.1", MONGO_PORT=27017,
        ...               MONGO_ACCOUNT_DB="mathematics", TIME_ZONE="UTC")
        >>> s.PORT
        8000
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    LOGGING: Literal["INFO", "DEBUG", "WARNING"] = "INFO"
    PORT: int = 8000
    TIME_ZONE: str = "UTC"

    MONGO_URL: str
    MONGO_PORT: int
    MONGO_ACCOUNT_DB: str
    MONGO_VARIABLES_COLLECTION: str = "variables"
    MONGO_JOBS_COLLECTION: str = "jobs"

    REDIS_URL: str = "redis://localhost:6379/0"

    IMMUTABLE_JOBS_DIR: Path = Path("jobs/immutable")


def get_settings() -> Settings:
    """Build a fresh `Settings` instance from the current environment/.env file."""
    return Settings()
