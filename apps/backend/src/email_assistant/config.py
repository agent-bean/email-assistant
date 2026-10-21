import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

STORE_CONFIG_ERROR = (
    "POSTGRES_PASSWORD, NEO4J_PASSWORD, QDRANT_API_KEY: "
    "set nonempty private credentials; see configuration template"
)


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
        raise ValueError(STORE_CONFIG_ERROR) from None


def validate_store_compose(command: list[str]) -> None:
    """Validate the credentials Compose will give services, without exposing its output."""
    private_source()
    try:
        result = subprocess.run(
            [*command, "config", "--format", "json"],
            check=True, capture_output=True, text=True, timeout=30,
        )
        services = json.loads(result.stdout)["services"]
        StoreSettings(
            _env_file=None,
            postgres_password=services["postgres"]["environment"]["POSTGRES_PASSWORD"],
            neo4j_password=services["neo4j"]["environment"]["NEO4J_AUTH"][len("neo4j/"):],
            qdrant_api_key=services["qdrant"]["environment"]["QDRANT__SERVICE__API_KEY"],
        )
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        raise ValueError(STORE_CONFIG_ERROR) from None


if __name__ == "__main__":
    try:
        validate_store_compose(sys.argv[1:])
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
