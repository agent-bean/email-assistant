import os
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_prefix="APP_")
    environment: Literal["local"] = "local"


def private_source() -> str | None:
    """Private files are opt-in; CI never discovers owner configuration."""
    source = os.environ.get("APP_ENV_FILE")
    if source:
        try:
            path = Path(source)
            if not path.is_file() or path.stat().st_mode & 0o077:
                raise OSError
        except OSError:
            raise ValueError("APP_ENV_FILE: choose an existing private file; chmod 600") from None
    return source or None


def load_settings() -> Settings:
    source = private_source()
    try:
        return Settings(_env_file=source)
    except (ValidationError, OSError, UnicodeError):
        raise ValueError("APP_ENVIRONMENT: use local; see configuration template") from None


class StoreSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    postgres_password: SecretStr = Field(min_length=16)
    neo4j_password: SecretStr = Field(min_length=16)
    qdrant_api_key: SecretStr = Field(min_length=32)


def load_store_settings() -> StoreSettings:
    source = private_source()
    try:
        return StoreSettings(_env_file=source)
    except (ValidationError, OSError, UnicodeError):
        raise ValueError(
            "POSTGRES_PASSWORD, NEO4J_PASSWORD, QDRANT_API_KEY: "
            "set nonempty private credentials; see configuration template"
        ) from None
