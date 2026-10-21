import os
import subprocess
import time
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from email_assistant.config import load_store_settings

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture(scope="module")
def stores():
    project = os.environ.get("STORE_TEST_PROJECT", "")
    if not project.startswith("email-assistant-test-"):
        pytest.fail(
            "Run make test-integration; persistence checks require backed-up disposable stores"
        )
    try:
        settings = load_store_settings()
    except ValueError as exc:
        pytest.fail(str(exc), pytrace=False)
    return settings


def postgres(password):
    import psycopg

    return psycopg.connect(
        host="127.0.0.1",
        port=5432,
        dbname="email_assistant",
        user="email_assistant",
        password=password,
        connect_timeout=3,
    )


def graph(password):
    from neo4j import GraphDatabase

    return GraphDatabase.driver(
        "bolt://127.0.0.1:7687",
        auth=("neo4j", password),
        connection_timeout=3,
        connection_acquisition_timeout=5,
        max_transaction_retry_time=0,
    )


def test_authentication(stores):
    import psycopg
    from neo4j.exceptions import AuthError

    try:
        with postgres(stores.postgres_password.get_secret_value()) as db:
            assert db.execute("SELECT 1").fetchone() == (1,)
        for password in ("invalid-password", ""):
            with pytest.raises(psycopg.OperationalError):
                postgres(password)
        with graph(stores.neo4j_password.get_secret_value()) as driver:
            assert driver.execute_query("RETURN 1 AS value").records[0]["value"] == 1
        for password in ("invalid-password", ""):
            with graph(password) as driver, pytest.raises(AuthError):
                driver.verify_connectivity()
        with httpx.Client(base_url="http://127.0.0.1:6333", timeout=3) as client:
            assert (
                client.get(
                    "/collections", headers={"api-key": stores.qdrant_api_key.get_secret_value()}
                ).status_code
                == 200
            )
            for headers in ({}, {"api-key": "invalid-key"}):
                assert client.get("/collections", headers=headers).status_code in (401, 403)
    except (psycopg.Error, httpx.HTTPError):
        pytest.fail(
            "Store authentication check failed; inspect service status privately", pytrace=False
        )


def test_restart_persistence_and_outage(stores):
    import psycopg

    project = os.environ["STORE_TEST_PROJECT"]
    command = [
        "docker",
        "compose",
        "--env-file",
        os.environ["APP_ENV_FILE"],
        "-f",
        str(ROOT / "deploy/compose.yaml"),
        "-p",
        project,
    ]
    token = uuid4().hex
    collection = "skeleton_check_" + token

    def compose(*args):
        result = subprocess.run(command + list(args), capture_output=True, timeout=200)
        assert result.returncode == 0, "Owned store lifecycle command failed"

    with (
        postgres(stores.postgres_password.get_secret_value()) as db,
        graph(stores.neo4j_password.get_secret_value()) as driver,
        httpx.Client(
            base_url="http://127.0.0.1:6333",
            timeout=5,
            headers={"api-key": stores.qdrant_api_key.get_secret_value()},
        ) as client,
    ):
        try:
            db.execute("CREATE TABLE skeleton_probe (id text PRIMARY KEY)")
            db.execute("INSERT INTO skeleton_probe VALUES (%s)", (token,))
            db.commit()
            driver.execute_query("CREATE (:SkeletonProbe {id: $id})", id=token)
            assert (
                client.put(
                    f"/collections/{collection}",
                    json={"vectors": {"size": 2, "distance": "Cosine"}},
                ).status_code
                == 200
            )
            assert (
                client.put(
                    f"/collections/{collection}/points",
                    params={"wait": "true"},
                    json={"points": [{"id": 1, "vector": [1.0, 0.0]}]},
                ).status_code
                == 200
            )
            compose("stop")
            started = time.monotonic()
            with pytest.raises(psycopg.OperationalError):
                postgres(stores.postgres_password.get_secret_value())
            with pytest.raises(Exception):
                with graph(stores.neo4j_password.get_secret_value()) as offline:
                    offline.verify_connectivity()
            with pytest.raises(httpx.HTTPError):
                client.get("/collections")
            assert time.monotonic() - started < 20
            from fastapi.testclient import TestClient

            from email_assistant.api.main import app

            with TestClient(app) as api:
                assert api.get("/health").json() == {"status": "ok"}
            compose("up", "-d", "--wait", "--wait-timeout", "180")
            with postgres(stores.postgres_password.get_secret_value()) as fresh:
                assert fresh.execute("SELECT id FROM skeleton_probe").fetchone() == (token,)
            assert (
                driver.execute_query(
                    "MATCH (n:SkeletonProbe {id: $id}) RETURN n.id AS id", id=token
                ).records[0]["id"]
                == token
            )
            assert client.get(f"/collections/{collection}/points/1").json()["result"]["id"] == 1
        finally:
            compose("up", "-d", "--wait", "--wait-timeout", "180")
            with postgres(stores.postgres_password.get_secret_value()) as fresh:
                fresh.execute("DROP TABLE IF EXISTS skeleton_probe")
            driver.execute_query("MATCH (n:SkeletonProbe {id: $id}) DELETE n", id=token)
            client.delete(f"/collections/{collection}")


def test_compose_requires_credentials(tmp_path, monkeypatch):
    for key in ("POSTGRES_PASSWORD", "NEO4J_PASSWORD", "QDRANT_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    config = tmp_path / "empty.conf"
    config.write_text("")
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            str(config),
            "-f",
            str(ROOT / "deploy/compose.yaml"),
            "config",
            "--quiet",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "Set " in result.stderr
