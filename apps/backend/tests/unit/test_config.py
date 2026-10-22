import subprocess
import sys

import pytest

from email_assistant.config import load_settings, load_store_settings

pytestmark = pytest.mark.unit


def test_optional_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV_FILE", raising=False)
    for key in ("LLM_API_KEY", "TAVILY_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.setenv(key, "")
    assert load_settings().environment == "local"


def test_invalid_setting_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "https://user:secret@example.invalid"
    monkeypatch.setenv("APP_ENVIRONMENT", secret)
    with pytest.raises(ValueError, match="APP_ENVIRONMENT") as error:
        load_settings()
    assert secret not in str(error.value)
    result = subprocess.run(
        [sys.executable, "-c", "from email_assistant.config import load_settings; load_settings()"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert secret not in result.stderr
    assert "configuration template" in result.stderr


def test_missing_explicit_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV_FILE", "/nonexistent/private-config")
    with pytest.raises(ValueError, match="APP_ENV_FILE"):
        load_settings()


def test_missing_active_store_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV_FILE", raising=False)
    for key in ("POSTGRES_PASSWORD", "NEO4J_PASSWORD", "QDRANT_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValueError, match="set nonempty private credentials"):
        load_store_settings()


def test_explicit_private_file_and_environment_precedence(tmp_path, monkeypatch):
    config = tmp_path / "private.conf"
    config.write_text("APP_ENVIRONMENT=invalid\nLLM_API_KEY=\n")
    config.chmod(0o600)
    monkeypatch.setenv("APP_ENV_FILE", str(config))
    with pytest.raises(ValueError, match="APP_ENVIRONMENT"):
        load_settings()
    monkeypatch.setenv("APP_ENVIRONMENT", "local")
    assert load_settings().environment == "local"


def test_private_file_permissions(tmp_path, monkeypatch):
    config = tmp_path / "private.conf"
    config.write_text("APP_ENVIRONMENT=local\n")
    config.chmod(0o644)
    monkeypatch.setenv("APP_ENV_FILE", str(config))
    with pytest.raises(ValueError, match="chmod 600"):
        load_settings()


def test_database_configuration_is_independent_and_sanitized(monkeypatch, tmp_path):
    from email_assistant.config import load_database_settings

    for key in list(__import__("os").environ):
        if key.startswith("STORAGE_") or key == "APP_ENV_FILE":
            monkeypatch.delenv(key)
    with pytest.raises(ValueError, match="STORAGE_"):
        load_database_settings()
    for key, value in dict(
        DATABASE="example",
        RUNTIME_USER="runtime",
        ADMIN_USER="admin",
        RUNTIME_PASSWORD="r" * 24,
        ADMIN_PASSWORD="a" * 24,
        ARTIFACT_ROOT=str(tmp_path),
    ).items():
        monkeypatch.setenv("STORAGE_" + key, value)
    assert load_database_settings().url().username == "runtime"
    assert load_database_settings().url(admin=True).username == "admin"
    monkeypatch.setenv("STORAGE_RUNTIME_USER", "admin")
    with pytest.raises(ValueError) as error:
        load_database_settings()
    assert "a" * 24 not in str(error.value)
    monkeypatch.setenv("STORAGE_RUNTIME_USER", "runtime")
    monkeypatch.delenv("STORAGE_ADMIN_USER")
    monkeypatch.delenv("STORAGE_ADMIN_PASSWORD")
    assert load_database_settings().url().username == "runtime"
    with pytest.raises(ValueError, match="maintenance credentials"):
        load_database_settings().url(admin=True)
