"""Tests may write only after matching owned container and a fresh logical/file backup."""

import os
import runpy
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import insert, text

from email_assistant.config import load_database_settings
from email_assistant.models.records import accounts
from email_assistant.persistence.database import engine_for, transaction, verify_runtime

ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture(scope="session")
def storage():
    project = os.environ.get("STORE_TEST_PROJECT", "")
    if not project.startswith("email-assistant-test-") or not os.environ.get("STORE_TEST_CLUSTER"):
        pytest.fail("Run make test-integration; owned backed-up disposable context required")
    settings = load_database_settings()
    directory = Path(os.environ["STORE_TEST_DIRECTORY"])
    assert settings.artifact_root == directory / "artifacts"
    assert settings.database == "email_assistant" and settings.runtime_user == "storage_runtime"
    engine = engine_for(settings, admin=True)
    with engine.connect() as connection:
        assert (
            str(
                connection.execute(
                    text("SELECT system_identifier FROM pg_control_system()")
                ).scalar_one()
            )
            == os.environ["STORE_TEST_CLUSTER"]
        )
    engine.dispose()
    return settings


@pytest.fixture(scope="session")
def snapshots():
    return runpy.run_path(str(ROOT / "scripts/storage-snapshot.py"))


@pytest.fixture(autouse=True)
def preimage(storage, snapshots):
    staging = Path(os.environ["STORE_TEST_DIRECTORY"]) / ("preimage-" + uuid4().hex)
    snapshots["backup"](storage, staging)
    return staging


@pytest.fixture
def db(storage, preimage):
    engine = engine_for(storage)
    with transaction(engine) as session:
        verify_runtime(session)
    yield engine
    engine.dispose()


@pytest.fixture
def account_id(db):
    identity = uuid4()
    with transaction(db) as session:
        session.execute(
            insert(accounts).values(
                id=identity, provider="fixture", subject=uuid4().hex, owner_subject="fixture-owner"
            )
        )
    return identity
