import os
import runpy
import shlex
import socket
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[4]
CREDENTIALS = {
    "POSTGRES_PASSWORD": "p" * 16,
    "NEO4J_PASSWORD": "n" * 16,
    "QDRANT_API_KEY": "q" * 32,
}


def test_port_probe_allows_closed_connections():
    ports_available = runpy.run_path(str(ROOT / "scripts/check-stores.py"))["ports_available"]
    with socket.socket() as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.settimeout(2)
        server.bind(("127.0.0.1", 0))
        port = server.getsockname()[1]
        server.listen()
        with socket.socket() as client:
            client.settimeout(2)
            client.connect(("127.0.0.1", port))
            connection, _ = server.accept()
            connection.close()
            assert client.recv(1) == b""
    with socket.socket() as probe, pytest.raises(OSError):
        probe.bind(("127.0.0.1", port))
    assert ports_available((port,))


@pytest.mark.parametrize("host", ["127.0.0.1", "0.0.0.0"])
def test_port_probe_rejects_active_listener(host, capsys):
    ports_available = runpy.run_path(str(ROOT / "scripts/check-stores.py"))["ports_available"]
    with socket.socket() as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, 0))
        server.listen()
        port = server.getsockname()[1]
        assert not ports_available((port,))
    assert f"Port {port} occupied" in capsys.readouterr().out


def stores_up(tmp_path, credentials, *, mode=0o600, overrides=None):
    config = tmp_path / "private config.conf"
    config.write_text("".join(f"{key}={value}\n" for key, value in credentials.items()))
    config.chmod(mode)
    env = {key: value for key, value in os.environ.items() if key not in CREDENTIALS}
    env.update(APP_ENV_FILE="/nonexistent/ignored-owner-config", **(overrides or {}))
    env.pop("REVIEW_UNSET_PADDING_LONG_ENOUGH", None)
    compose = tmp_path / "compose.py"
    compose.write_text(
        "import os, sys\n"
        "if 'config' in sys.argv[1:]:\n"
        "    os.execvp('docker', ['docker', 'compose', *sys.argv[1:]])\n"
        "assert sys.argv[-5:] == ['up', '-d', '--wait', '--wait-timeout', '180']\n"
        "print('COMPOSE_CALLED', *sys.argv[-5:])\n"
    )
    command = shlex.join([
        sys.executable, str(compose), "--env-file", str(config),
        "-f", str(ROOT / "deploy/compose.yaml"), "-p", "email-assistant-dev",
    ])
    # Resolve with real Compose; intercept startup so these tests never touch stores.
    return subprocess.run(
        [
            "make",
            "--no-print-directory",
            "stores-up",
            f"ENV_FILE={os.path.relpath(config, ROOT)}",
            f"COMPOSE={command}",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.mark.parametrize("key", CREDENTIALS)
def test_stores_up_rejects_short_credentials_before_startup(tmp_path, key):
    secret = "https://u:s@x"
    result = stores_up(tmp_path, {**CREDENTIALS, key: secret})
    assert result.returncode != 0
    assert "configuration template" in result.stderr
    assert "COMPOSE_CALLED" not in result.stdout
    assert secret not in result.stdout + result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("credentials,mode", [({}, 0o600), (CREDENTIALS, 0o644)])
def test_stores_up_rejects_missing_credentials_or_public_file(tmp_path, credentials, mode):
    result = stores_up(tmp_path, credentials, mode=mode)
    assert result.returncode != 0
    assert "COMPOSE_CALLED" not in result.stdout
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("override", [False, True])
def test_stores_up_accepts_valid_credentials_and_environment_precedence(tmp_path, override):
    credentials = {key: "short" for key in CREDENTIALS} if override else CREDENTIALS
    result = stores_up(tmp_path, credentials, overrides=CREDENTIALS if override else {})
    assert result.returncode == 0, result.stderr
    assert "COMPOSE_CALLED up -d --wait --wait-timeout 180" in result.stdout


def test_stores_up_rejects_short_environment_override(tmp_path):
    result = stores_up(tmp_path, CREDENTIALS, overrides={"QDRANT_API_KEY": "short"})
    assert result.returncode != 0
    assert "COMPOSE_CALLED" not in result.stdout


@pytest.mark.parametrize("key", CREDENTIALS)
def test_stores_up_validates_interpolated_credentials(tmp_path, key):
    result = stores_up(tmp_path, {**CREDENTIALS, key: "short$REVIEW_UNSET_PADDING_LONG_ENOUGH"})
    assert result.returncode != 0
    assert "configuration template" in result.stderr
    assert "COMPOSE_CALLED" not in result.stdout


def test_stores_up_accepts_literal_dollars_and_expansion(tmp_path):
    credentials = {
        "POSTGRES_PASSWORD": "'literal$" + "p" * 16 + "'",
        "NEO4J_PASSWORD": "$REVIEW_VALID_PASSWORD",
        "QDRANT_API_KEY": "'literal$" + "q" * 32 + "'",
    }
    result = stores_up(tmp_path, credentials, overrides={"REVIEW_VALID_PASSWORD": "n" * 16})
    assert result.returncode == 0, result.stderr
    assert "COMPOSE_CALLED up" in result.stdout


def test_stores_up_sanitizes_compose_parse_errors(tmp_path):
    secret = "https://u:private@example.invalid"
    result = stores_up(tmp_path, {**CREDENTIALS, "BROKEN": "'" + secret})
    assert result.returncode != 0
    assert "configuration template" in result.stderr
    assert "COMPOSE_CALLED" not in result.stdout
    assert secret not in result.stdout + result.stderr
    assert "Traceback" not in result.stderr
