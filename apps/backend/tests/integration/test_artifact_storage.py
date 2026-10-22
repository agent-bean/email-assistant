import hashlib
from io import BytesIO

import pytest
from sqlalchemy import select

from email_assistant.models import records as m
from email_assistant.persistence.artifacts import inspect_files, prepare, publish, verify_file
from email_assistant.persistence.database import Conflict, StorageError, transaction
from email_assistant.persistence.workflows import create_action

pytestmark = pytest.mark.integration


def test_ready_pending_and_retention(storage, db, account_id):
    data = b"permitted synthetic attachment"
    checksum = hashlib.sha256(data).hexdigest()
    with transaction(db) as session:
        identity = prepare(
            session, account_id, checksum, len(data), "text/plain", "attachment", "temporary"
        )
        retained = prepare(
            session, account_id, checksum, len(data), "text/plain", "report", "approved_report"
        )
    with transaction(db) as session:
        publish(session, storage.artifact_root, identity, BytesIO(data))
        publish(session, storage.artifact_root, retained, BytesIO(data))
    with transaction(db) as session:
        row = (
            session.execute(select(m.artifacts).where(m.artifacts.c.id == identity))
            .mappings()
            .one()
        )
        verify_file(storage.artifact_root, row.storage_key, checksum, len(data))
        assert row.expires_at is not None
        row2 = (
            session.execute(select(m.artifacts).where(m.artifacts.c.id == retained))
            .mappings()
            .one()
        )
        assert row2.expires_at is None and row2.storage_key != row.storage_key
        create_action(
            session,
            account_id,
            "forward_report",
            "artifact-action",
            {},
            ["recipient@example.test"],
            [{"id": str(identity), "hash": checksum}],
            "r1",
        )
    with pytest.raises(StorageError), transaction(db) as session:
        create_action(
            session,
            account_id,
            "forward_report",
            "bad-artifact-action",
            {},
            ["recipient@example.test"],
            [{"id": str(identity), "hash": "1" * 64}],
            "r1",
        )


def test_crash_points_detectable_without_false_ready(storage, db, account_id):
    data = b"fixture bytes"
    checksum = hashlib.sha256(data).hexdigest()
    with transaction(db) as session:
        identity = prepare(
            session, account_id, checksum, len(data), "text/plain", "attachment", "temporary"
        )
    with pytest.raises(Conflict), transaction(db) as session:
        publish(session, storage.artifact_root, identity, BytesIO(data))
        raise Conflict("crash after file fsync, before DB commit")
    with transaction(db) as session:
        detected = inspect_files(session, storage.artifact_root)
        assert str(identity) in detected["pending"]
        assert detected["missing_ready"] == []
        row = (
            session.execute(select(m.artifacts).where(m.artifacts.c.id == identity))
            .mappings()
            .one()
        )
        verify_file(storage.artifact_root, row.storage_key, checksum, len(data))
        broken = prepare(
            session, account_id, checksum, len(data), "text/plain", "attachment", "temporary"
        )
    with pytest.raises(StorageError), transaction(db) as session:
        publish(session, storage.artifact_root, broken, BytesIO(b"wrong"))
    with transaction(db) as session:
        detected = inspect_files(session, storage.artifact_root)
        assert str(broken) in detected["pending"] and detected["unreferenced"]
        assert detected["missing_ready"] == []
