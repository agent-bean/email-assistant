import hashlib
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from email_assistant.models import records as m
from email_assistant.persistence import workflows as w
from email_assistant.persistence.artifacts import prepare, publish
from email_assistant.persistence.database import StorageError, engine_for, transaction
from email_assistant.persistence.projections import acknowledge, append_revision, create_record

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[4]


def isolated_database(storage, tmp_path):
    from psycopg import sql

    name = "restore_" + uuid4().hex
    engine = engine_for(storage, admin=True).execution_options(isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            connection.connection.driver_connection.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name))
            )
    finally:
        engine.dispose()
    root = tmp_path / name
    root.mkdir(mode=0o700)
    return storage.model_copy(update={"database": name, "artifact_root": root})


def test_matched_restore_and_restart(storage, snapshots, db, account_id, tmp_path):
    data = b"permitted synthetic retained report"
    with transaction(db) as session:
        for kind in ("company", "contact", "source", "meeting"):
            identity = create_record(session, account_id, kind)
            append_revision(session, identity, {"fixture": kind}, "r1")
        report = create_record(session, account_id, "report")
        append_revision(session, report, {"text": "permitted synthetic report"}, "r1")
        artifact = prepare(
            session,
            account_id,
            hashlib.sha256(data).hexdigest(),
            len(data),
            "text/plain",
            "report",
            "approved_report",
            record_id=report,
            source_revision=1,
        )
    with transaction(db) as session:
        publish(session, storage.artifact_root, artifact, BytesIO(data))
        action = w.create_action(
            session,
            account_id,
            "send_reply",
            uuid4().hex,
            {"body": "fixture"},
            ["recipient@example.test"],
            [],
            "r1",
        )
        w.transition_action(session, action, "draft", 0, "awaiting_approval")
        w.decide(session, action, 1, 1, "fixture-owner", "approved", "decision-" + uuid4().hex)
        attempt = w.claim(session, action, 2)
        w.finish(session, action, 3, attempt["claim_token"], attempt["fence"], "unknown")
        run = w.create_run(session, account_id, "research", uuid4().hex, "r1")
        w.transition_run(session, run, "queued", 0, "running")
        w.save_step(session, run, "done", "r1", "input:1", "output:1")
        w.save_step(session, run, "pending", "r1", "input:2")
        event = session.execute(
            select(m.outbox.c.id).where(m.outbox.c.entity_id == report)
        ).scalar_one()
        acknowledge(session, event, "neo4j", 0)
    snapshot = tmp_path / "matched-snapshot"
    manifest = snapshots["backup"](storage, snapshot)
    db.dispose()
    command = [
        "docker",
        "compose",
        "--env-file",
        os.environ["APP_ENV_FILE"],
        "-f",
        str(ROOT / "deploy/compose.yaml"),
        "-p",
        os.environ["STORE_TEST_PROJECT"],
    ]
    for args in [("stop", "postgres"), ("up", "-d", "--wait", "--wait-timeout", "180", "postgres")]:
        result = subprocess.run([*command, *args], capture_output=True, timeout=200)
        assert result.returncode == 0
    # A fresh process, not an existing SQLAlchemy session, checks durable canonical state.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from email_assistant.config import load_database_settings; "
            "from email_assistant.persistence.database import engine_for,transaction; "
            "from sqlalchemy import text; "
            "e=engine_for(load_database_settings()); "
            "s=e.connect(); "
            "assert {'company','contact','source','meeting','report','action'} <= "
            "set(s.execute(text('SELECT DISTINCT record_type FROM records')).scalars()); "
            'assert s.execute(text("SELECT count(*) FROM actions '
            "WHERE state='unknown'\")).scalar_one()>0; "
            'assert s.execute(text("SELECT count(*) FROM run_steps '
            "WHERE state='completed'\")).scalar_one()>0; "
            "s.close();e.dispose()",
        ],
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 0
    with snapshots["maintenance"](storage) as connection:
        assert snapshots["fingerprints"](connection) == manifest["fingerprints"]
    destination = isolated_database(storage, tmp_path)
    # Source defaults to UTC; restore must compare timestamps independently of target zone.
    from psycopg import sql

    admin = engine_for(destination, admin=True).execution_options(isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            connection.connection.driver_connection.execute(
                sql.SQL("ALTER DATABASE {} SET timezone TO 'Asia/Bangkok'").format(
                    sql.Identifier(destination.database)
                )
            )
    finally:
        admin.dispose()
    snapshots["restore"](destination, snapshot, isolated=True)
    with snapshots["maintenance"](destination) as connection:
        assert snapshots["fingerprints"](connection) == manifest["fingerprints"]
        assert (
            connection.execute(
                text("SELECT state FROM actions WHERE id=:id"), {"id": action}
            ).scalar_one()
            == "unknown"
        )
        snapshots["verify_artifacts"](connection, destination.artifact_root)
    runtime = engine_for(destination)
    try:
        with transaction(runtime) as session:
            assert (
                session.execute(
                    select(m.actions.c.state).where(m.actions.c.id == action)
                ).scalar_one()
                == "unknown"
            )
            restored_run = w.create_run(session, account_id, "restore-write", uuid4().hex, "r1")
        with transaction(runtime) as session:
            assert (
                session.execute(select(m.runs.c.id).where(m.runs.c.id == restored_run)).scalar_one()
                == restored_run
            )
        with pytest.raises(StorageError), transaction(runtime) as session:
            session.execute(text("CREATE TABLE forbidden_restore_probe (id int)"))
    finally:
        runtime.dispose()
    with pytest.raises(StorageError):
        snapshots["restore"](destination, snapshot, isolated=True)
    with pytest.raises(StorageError):
        snapshots["restore"](storage, snapshot, isolated=True)


def test_snapshot_refusals_and_corruption(storage, snapshots, tmp_path):
    snapshot = tmp_path / "snapshot"
    snapshots["backup"](storage, snapshot)
    with pytest.raises(StorageError):
        snapshots["backup"](storage, snapshot)
    unsafe = tmp_path / "link"
    unsafe.symlink_to(snapshot, target_is_directory=True)
    with pytest.raises(StorageError):
        snapshots["backup"](storage, unsafe / "nested")
    corrupt = tmp_path / "corrupt"
    shutil.copytree(snapshot, corrupt)
    with (corrupt / "database.dump").open("ab") as stream:
        stream.write(b"corrupt")
    destination = isolated_database(storage, tmp_path)
    with pytest.raises(StorageError, match="Corrupt"):
        snapshots["restore"](destination, corrupt, isolated=True)
    with snapshots["maintenance"](destination) as connection:
        assert snapshots["fingerprints"](connection)["tables"] == {}
    if list((snapshot / "artifacts").iterdir()):
        missing = tmp_path / "missing"
        shutil.copytree(snapshot, missing)
        next((missing / "artifacts").iterdir()).unlink()
        with pytest.raises(StorageError):
            snapshots["restore"](destination, missing, isolated=True)
    with pytest.raises(StorageError):
        snapshots["restore"](destination, snapshot)


def test_restore_provisions_separate_new_runtime_role(storage, snapshots, tmp_path):
    snapshot = tmp_path / "new-role-snapshot"
    snapshots["backup"](storage, snapshot)
    destination = isolated_database(storage, tmp_path).model_copy(
        update={"runtime_user": "restored_" + uuid4().hex}
    )
    snapshots["restore"](destination, snapshot, isolated=True, provision=True)
    runtime = engine_for(destination)
    try:
        with transaction(runtime) as session:
            session.execute(text("SELECT id FROM accounts LIMIT 1")).first()
            identity = uuid4()
            session.execute(
                m.accounts.insert().values(
                    id=identity,
                    provider="fixture",
                    subject=uuid4().hex,
                    owner_subject="fixture-owner",
                )
            )
        with pytest.raises(StorageError), transaction(runtime) as session:
            session.execute(text("CREATE TABLE forbidden_new_role_probe (id int)"))
    finally:
        runtime.dispose()


def test_backup_and_upgrade_failure_preserve_source(storage, snapshots, tmp_path, monkeypatch):
    with snapshots["maintenance"](storage) as connection:
        before = snapshots["fingerprints"](connection)

    def fail(*args, **kwargs):
        raise StorageError("permitted injected operation failure")

    with monkeypatch.context() as patch:
        patch.setitem(snapshots["backup"].__globals__, "pg_tool", fail)
        with pytest.raises(StorageError):
            snapshots["migrate"](storage, tmp_path / "failed-backup")
    assert not (tmp_path / "failed-backup/manifest.json").exists()

    def interrupted(config, head):
        config.attributes["connection"].execute(text("CREATE TABLE interrupted_probe (id int)"))
        raise StorageError("permitted interrupted migration")

    with monkeypatch.context() as patch:
        patch.setattr(snapshots["command"], "upgrade", interrupted)
        with pytest.raises(StorageError):
            snapshots["migrate"](storage, tmp_path / "before-interruption")
    assert (tmp_path / "before-interruption/manifest.json").is_file()
    with snapshots["maintenance"](storage) as connection:
        assert snapshots["fingerprints"](connection) == before
    destination = isolated_database(storage, tmp_path)
    snapshots["restore"](destination, tmp_path / "before-interruption", isolated=True)


def test_writer_exclusion_in_backup_to_upgrade_gap(
    storage, snapshots, db, account_id, tmp_path, monkeypatch
):
    original = snapshots["backup_locked"]
    key = uuid4().hex

    def write():
        with transaction(db) as session:
            return w.create_run(session, account_id, "fixture", key, "r1")

    def hold_after_dump(connection, settings, staging):
        result = original(connection, settings, staging)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(write)
            with pytest.raises(StorageError):
                future.result(timeout=8)
        return result

    with monkeypatch.context() as patch:
        patch.setitem(snapshots["migrate"].__globals__, "backup_locked", hold_after_dump)
        snapshots["migrate"](storage, tmp_path / "excluded-upgrade")
    with transaction(db) as session:
        assert session.execute(select(m.runs).where(m.runs.c.logical_key == key)).first() is None


def test_unknown_revision_blocks_upgrade(storage, snapshots, tmp_path):
    destination = isolated_database(storage, tmp_path)
    snapshots["migrate"](destination, tmp_path / "empty-before-upgrade")
    # This sequence has a preimage before intentionally corrupting only disposable metadata.
    snapshots["backup"](destination, tmp_path / "before-incompatible")
    admin = engine_for(destination, admin=True)
    try:
        with admin.begin() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num='unknown_future'"))
    finally:
        admin.dispose()
    with pytest.raises(StorageError, match="Unknown database revision"):
        snapshots["migrate"](destination, tmp_path / "refused-upgrade")
    assert not (tmp_path / "refused-upgrade/manifest.json").exists()
