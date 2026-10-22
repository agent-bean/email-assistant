"""Local PostgreSQL 17 + private-file snapshots. Production restic/R2 belongs to #42."""

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from email_assistant.config import DatabaseSettings, load_database_settings
from email_assistant.persistence.artifacts import private_root, verify_file
from email_assistant.persistence.database import (
    MAINTENANCE_KEY,
    StorageError,
    engine_for,
    grant_runtime,
    provision_runtime,
    verify_runtime,
)

ROOT = Path(__file__).resolve().parents[1]


def alembic_config() -> Config:
    return Config(str(ROOT / "apps/backend/alembic.ini"))


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def overlap(first: Path, second: Path) -> bool:
    return first == second or first in second.parents or second in first.parents


def private_file(path: Path) -> None:
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or (stat.S_IMODE(info.st_mode) & 0o077)
        or info.st_nlink != 1
    ):
        raise StorageError("Snapshot contains unsafe file")


def pg_tool(program: str, settings: DatabaseSettings, *args: str) -> None:
    settings.url(admin=True)
    assert settings.admin_user is not None and settings.admin_password is not None
    environment = {
        "PATH": os.environ["PATH"],
        "LC_ALL": "C",
        "PGHOST": settings.host,
        "PGPORT": str(settings.port),
        "PGDATABASE": settings.database,
        "PGUSER": settings.admin_user,
        "PGPASSWORD": settings.admin_password.get_secret_value(),
        "PGCONNECT_TIMEOUT": "3",
    }
    version = subprocess.run(
        [program, "--version"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if version.returncode or "(PostgreSQL) 17." not in version.stdout:
        raise StorageError("PostgreSQL 17 client required")
    result = subprocess.run(
        [program, *args], env=environment, capture_output=True, timeout=180
    )
    if result.returncode:
        raise StorageError("PostgreSQL snapshot operation failed; inspect privately")


def db_identity(connection: Connection, settings: DatabaseSettings) -> None:
    row = connection.execute(
        text(
            "SELECT current_database(),current_user,inet_server_port(),"
            "current_setting('server_version_num')::int"
        )
    ).one()
    if tuple(row[:3]) != (
        settings.database,
        settings.admin_user,
        settings.port,
    ) or not (170000 <= row[3] < 180000):
        raise StorageError("Resolved database identity/version mismatch")


@contextmanager
def maintenance(settings: DatabaseSettings) -> Iterator[Connection]:
    engine = engine_for(settings, admin=True)
    try:
        with engine.connect() as connection:
            db_identity(connection, settings)
            acquired = connection.execute(
                text("SELECT pg_try_advisory_lock(:key)"), {"key": MAINTENANCE_KEY}
            ).scalar_one()
            if not acquired:
                raise StorageError(
                    "Active writer or maintenance operation; stop writers first"
                )
            # Hold session exclusion through backup, subprocesses, upgrade and all failure paths.
            try:
                connection.commit()
                yield connection
            finally:
                connection.rollback()
                connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"), {"key": MAINTENANCE_KEY}
                )
                connection.commit()
    finally:
        engine.dispose()


def revision(connection: Connection) -> str | None:
    exists = connection.execute(
        text("SELECT to_regclass('public.alembic_version')")
    ).scalar_one()
    if exists is None:
        return None
    values = list(
        connection.execute(text("SELECT version_num FROM alembic_version")).scalars()
    )
    if len(values) != 1:
        raise StorageError("Expected one database revision")
    return str(values[0])


def check_revision(connection: Connection) -> str | None:
    scripts = ScriptDirectory.from_config(alembic_config())
    if len(scripts.get_heads()) != 1:
        raise StorageError("Expected one migration head")
    current = revision(connection)
    if current is not None and current not in {
        r.revision for r in scripts.walk_revisions()
    }:
        raise StorageError("Unknown database revision; abort migration")
    return current


def fingerprints(connection: Connection) -> dict[str, Any]:
    from psycopg import sql

    connection.execute(text("SET LOCAL TIME ZONE 'UTC'"))
    raw = connection.connection.driver_connection
    tables = list(
        connection.execute(
            text(
                "SELECT tablename FROM pg_tables WHERE "
                "schemaname='public' ORDER BY tablename"
            )
        ).scalars()
    )
    result = {}
    for name in tables:
        hashed = hashlib.sha256()
        count = 0
        query = sql.SQL(
            'SELECT row_to_json(t)::text FROM {} t ORDER BY row_to_json(t)::text COLLATE "C"'
        ).format(sql.Identifier(name))
        with raw.cursor() as cursor:
            cursor.execute(query)
            for row in cursor:
                hashed.update(row[0].encode() + b"\n")
                count += 1
        result[name] = {"count": count, "sha256": hashed.hexdigest()}
    constraints = list(
        connection.execute(
            text("""
        SELECT c.relname, p.conname, pg_get_constraintdef(p.oid)
        FROM pg_constraint p JOIN pg_class c ON c.oid=p.conrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public'
        ORDER BY 1,2
    """)
        ).tuples()
    )
    triggers = list(
        connection.execute(
            text("""
        SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid) FROM pg_trigger t
        JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY 1,2
    """)
        ).tuples()
    )
    return {
        "tables": result,
        "constraints": [list(row) for row in constraints],
        "triggers": [list(row) for row in triggers],
    }


def verify_artifacts(connection: Connection, root: Path) -> None:
    if (
        connection.execute(text("SELECT to_regclass('public.artifacts')")).scalar_one()
        is None
    ):
        return
    for key, checksum, length in connection.execute(
        text(
            "SELECT storage_key,checksum,byte_length FROM artifacts WHERE state='ready'"
        )
    ):
        verify_file(root, key, checksum, length)


def backup_locked(
    connection: Connection, settings: DatabaseSettings, staging: Path
) -> dict[str, Any]:
    staging = staging.absolute()
    root = settings.artifact_root
    if overlap(staging, root) or any(
        p.is_symlink() for p in (staging, *staging.parents)
    ):
        raise StorageError("Snapshot staging overlaps source or contains symlink")
    with private_root(staging.parent), private_root(root):
        staging.mkdir(mode=0o700)  # Exclusive creation; no shared/reused staging.
    try:
        current = check_revision(connection)
        verify_artifacts(connection, root)
        before = fingerprints(connection)
        connection.commit()
        dump = staging / "database.dump"
        pg_tool(
            "pg_dump",
            settings,
            "--format=custom",
            "--no-owner",
            "--no-acl",
            "--file",
            str(dump),
        )
        dump.chmod(0o600)
        pg_tool("pg_restore", settings, "--list", str(dump))
        files = staging / "artifacts"
        files.mkdir(mode=0o700)
        manifest_files = {}
        for path in sorted(root.iterdir()):
            private_file(path)
            if not __import__("re").fullmatch(r"[0-9a-f]{32}(?:\.part)?", path.name):
                raise StorageError("Unexpected artifact filename")
            shutil.copyfile(path, files / path.name, follow_symlinks=False)
            (files / path.name).chmod(0o600)
            manifest_files[path.name] = digest(files / path.name)
        if before != fingerprints(connection):
            raise StorageError("Database changed during snapshot; stop all writers")
        manifest = {
            "format": 1,
            "revision": current,
            "database": settings.database,
            "host": settings.host,
            "port": settings.port,
            "artifact_root": str(root),
            "dump_sha256": digest(dump),
            "files": manifest_files,
            "fingerprints": before,
        }
        output = staging / "manifest.json"
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(manifest, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        return manifest
    except Exception:
        # Incomplete staging is evidence, never success. Operator can inspect/remove privately.
        (staging / "manifest.json").unlink(missing_ok=True)
        raise


def backup(settings: DatabaseSettings, staging: Path) -> dict[str, Any]:
    with maintenance(settings) as connection:
        return backup_locked(connection, settings, staging)


def migrate(
    settings: DatabaseSettings, staging: Path, *, provision: bool = False
) -> None:
    with maintenance(settings) as connection:
        backup_locked(connection, settings, staging)
        config = alembic_config()
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        connection.commit()
        with Session(bind=connection) as session, session.begin():
            if provision:
                provision_runtime(session, settings)
            else:
                grant_runtime(session, settings)
        connection.commit()
        verify_runtime_connection(settings)


def verify_runtime_connection(settings: DatabaseSettings) -> None:
    runtime = engine_for(settings)
    try:
        with Session(runtime) as session:
            verify_runtime(session)
            session.execute(text("SELECT id FROM accounts LIMIT 1")).first()
    finally:
        runtime.dispose()


def validate_snapshot(snapshot: Path) -> dict[str, Any]:
    with private_root(snapshot), private_root(snapshot / "artifacts"):
        private_file(snapshot / "manifest.json")
        manifest = json.loads((snapshot / "manifest.json").read_text())
        if manifest["format"] != 1 or set(manifest["files"]) != {
            p.name for p in (snapshot / "artifacts").iterdir()
        }:
            raise StorageError("Incomplete snapshot")
        private_file(snapshot / "database.dump")
        if digest(snapshot / "database.dump") != manifest["dump_sha256"]:
            raise StorageError("Corrupt database dump")
        for key, expected in manifest["files"].items():
            if not __import__("re").fullmatch(r"[0-9a-f]{32}(?:\.part)?", key):
                raise StorageError("Unsafe snapshot artifact key")
            path = snapshot / "artifacts" / key
            private_file(path)
            if digest(path) != expected:
                raise StorageError("Corrupt snapshot artifact")
        return manifest


def restore(
    settings: DatabaseSettings,
    snapshot: Path,
    *,
    isolated: bool = False,
    provision: bool = False,
) -> None:
    if not isolated:
        raise StorageError(
            "Explicit isolated restore target required; sending/scheduling disabled"
        )
    manifest = validate_snapshot(snapshot)
    root = settings.artifact_root
    if (settings.host, settings.port, settings.database) == (
        manifest["host"],
        manifest["port"],
        manifest["database"],
    ) or any(overlap(root, p) for p in (snapshot, Path(manifest["artifact_root"]))):
        raise StorageError("Restore overlaps source/snapshot")
    with private_root(root):
        if any(root.iterdir()):
            raise StorageError("Restore artifact destination must be empty")
    with maintenance(settings) as connection:
        objects = connection.execute(
            text(
                "SELECT count(*) FROM pg_class c JOIN pg_namespace n "
                "ON n.oid=c.relnamespace WHERE n.nspname NOT IN "
                "('pg_catalog','information_schema') "
                "AND n.nspname NOT LIKE 'pg_toast%' "
                "AND c.relkind IN ('r','v','m','S','f','p')"
            )
        ).scalar_one()
        sessions = connection.execute(
            text(
                "SELECT count(*) FROM pg_stat_activity WHERE "
                "datname=current_database() AND pid<>pg_backend_pid()"
            )
        ).scalar_one()
        if objects or sessions:
            raise StorageError("Restore database must be empty and offline")
        # Even an empty restore destination gets a preimage backup before mutation.
        preimage = snapshot.parent / (
            "restore-preimage-" + __import__("uuid").uuid4().hex
        )
        backup_locked(connection, settings, preimage)
        connection.commit()
        pg_tool(
            "pg_restore",
            settings,
            "--exit-on-error",
            "--single-transaction",
            "--no-owner",
            "--no-acl",
            "--dbname",
            settings.database,
            str(snapshot / "database.dump"),
        )
        for key in manifest["files"]:
            with (snapshot / "artifacts" / key).open("rb") as source:
                fd = os.open(
                    root / key,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                )
                with os.fdopen(fd, "wb") as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
                    output.flush()
                    os.fsync(output.fileno())
        if (
            revision(connection) != manifest["revision"]
            or fingerprints(connection) != manifest["fingerprints"]
        ):
            raise StorageError("Restore schema/records/constraints mismatch")
        verify_artifacts(connection, root)
        with Session(bind=connection) as session, session.begin():
            if provision:
                provision_runtime(session, settings)
            else:
                grant_runtime(session, settings)
        connection.commit()
        verify_runtime_connection(settings)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("backup", "migrate", "restore"))
    parser.add_argument("--config", required=True)
    parser.add_argument("--staging", type=Path)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--isolated", action="store_true")
    parser.add_argument("--provision-runtime", action="store_true")
    args = parser.parse_args()
    os.environ["APP_ENV_FILE"] = args.config
    os.umask(0o077)
    try:
        settings = load_database_settings()
        if args.operation == "restore":
            if args.snapshot is None:
                raise StorageError("--snapshot required")
            restore(
                settings,
                args.snapshot.absolute(),
                isolated=args.isolated,
                provision=args.provision_runtime,
            )
        else:
            if args.staging is None:
                raise StorageError("--staging required")
            if args.operation == "migrate":
                migrate(settings, args.staging, provision=args.provision_runtime)
            else:
                backup(settings, args.staging)
        print(
            "Local storage operation verified; production recovery remains downstream."
        )
        return 0
    except Exception as error:
        if isinstance(error, StorageError):
            print(str(error))
        print("Storage operation failed; inspect configuration/snapshot privately.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
