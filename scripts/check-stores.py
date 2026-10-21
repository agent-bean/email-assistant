"""Check disposable stores on fixed ports; never attach to existing data."""

import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    def terminate(signum, frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, terminate)
    for port in (5432, 7687, 6333):
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                print(f"Port {port} occupied; identify its owner and stop local dev stores first.")
                return 1
    project = "email-assistant-test-" + secrets.token_hex(6)
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in (
            "POSTGRES_PASSWORD",
            "NEO4J_PASSWORD",
            "QDRANT_API_KEY",
            "APP_ENV_FILE",
        )
    }
    with tempfile.TemporaryDirectory(prefix="email-assistant-stores-") as directory:
        config = Path(directory) / "private.conf"
        config.write_text(
            "".join(
                f"{key}={secrets.token_hex(24)}\n"
                for key in ("POSTGRES_PASSWORD", "NEO4J_PASSWORD", "QDRANT_API_KEY")
            )
        )
        config.chmod(0o600)
        command = [
            "docker",
            "compose",
            "--env-file",
            str(config),
            "-f",
            str(ROOT / "deploy/compose.yaml"),
            "-p",
            project,
        ]
        env.update(APP_ENV_FILE=str(config), STORE_TEST_PROJECT=project)

        def compose(*args: str) -> str:
            result = subprocess.run(command + list(args), env=env, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(f"Compose {args[0]} failed; inspect service status privately")
            return result.stdout

        try:
            compose("config", "--quiet")
            compose("up", "-d", "--wait", "--wait-timeout", "180")
            containers = [
                json.loads(line) for line in compose("ps", "--format", "json").splitlines()
            ]
            assert len(containers) == 3, "Expected three running containers"
            ids = [item["ID"] for item in containers]
            details = json.loads(subprocess.check_output(["docker", "inspect", *ids], text=True))
            volumes = []
            for item in details:
                for bindings in item["HostConfig"]["PortBindings"].values():
                    assert all(binding["HostIp"] == "127.0.0.1" for binding in bindings)
                assert len(item["NetworkSettings"]["Networks"]) == 1
                published = item["NetworkSettings"]["Ports"]
                assert any(published.values()), "Docker did not publish loopback ports"
                assert all(
                    binding["HostIp"] == "127.0.0.1"
                    for bindings in published.values()
                    if bindings
                    for binding in bindings
                )
                volumes.extend(
                    mount["Name"]
                    for mount in item["Mounts"]
                    if mount["Type"] == "volume"
                    and mount["Destination"]
                    in ("/data", "/var/lib/postgresql/data", "/qdrant/storage")
                )
            assert len(set(volumes)) == 3, "Expected three independent data volumes"
            network = json.loads(
                subprocess.check_output(
                    ["docker", "network", "inspect", project + "_stores"], text=True
                )
            )[0]
            assert network["Driver"] == "bridge"
            assert network["Name"] == project + "_stores"
            backup_image = next(
                item["Config"]["Image"]
                for item in details
                if item["Config"]["Labels"]["com.docker.compose.service"] == "postgres"
            )
            # Consistent offline backup of fresh stores, before any test mutation.
            compose("stop")
            for number, volume in enumerate(volumes):
                backup = subprocess.run(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "--network",
                        "none",
                        "--user",
                        "0",
                        "-v",
                        volume + ":/source:ro",
                        "-v",
                        directory + ":/backup",
                        "--entrypoint",
                        "tar",
                        backup_image,
                        "-czf",
                        f"/backup/store-{number}.tgz",
                        "-C",
                        "/source",
                        ".",
                    ],
                    capture_output=True,
                )
                if backup.returncode:
                    raise RuntimeError("Disposable store backup failed before mutation")
                assert (Path(directory) / f"store-{number}.tgz").stat().st_size > 0
            compose("up", "-d", "--wait", "--wait-timeout", "180")
            print(
                "Three stores ready; loopback/private bridge/volumes verified; backup complete.",
                flush=True,
            )
            return subprocess.run(
                [
                    "uv",
                    "run",
                    "--locked",
                    "--group",
                    "integration",
                    "pytest",
                    "-m",
                    "integration",
                    "--tb=short",
                ],
                cwd=ROOT / "apps/backend",
                env=env,
            ).returncode
        except (RuntimeError, AssertionError, subprocess.SubprocessError) as exc:
            print(
                "Store check failed:",
                str(exc) if isinstance(exc, (AssertionError, RuntimeError)) else type(exc).__name__,
            )
            status = subprocess.run(
                command + ["ps", "--format", "{{.Service}} {{.State}} {{.Health}}"],
                env=env,
                capture_output=True,
                text=True,
            )
            print(status.stdout)
            return 1
        finally:
            # This random project and its volumes were created by this invocation only.
            cleanup = subprocess.run(
                command + ["down", "--volumes", "--remove-orphans"], env=env, capture_output=True
            )
            if cleanup.returncode:
                raise RuntimeError(f"Cleanup failed for owned project {project}; stop it manually")
            print(
                f"Removed owned disposable project {project} and its backed-up volumes.", flush=True
            )


if __name__ == "__main__":
    sys.exit(main())
