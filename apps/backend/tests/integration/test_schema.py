from datetime import UTC, datetime
from uuid import uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import insert, select, text, update

from email_assistant.models import records as m
from email_assistant.persistence.database import StorageError, engine_for, transaction
from email_assistant.persistence.projections import append_revision, create_record
from email_assistant.persistence.workflows import create_run, retry_run, transition_run

pytestmark = pytest.mark.integration


def test_schema_matches_frozen_migrations(storage, snapshots, tmp_path):
    with snapshots["maintenance"](storage) as connection:
        assert snapshots["revision"](connection) == "0003"
        assert compare_metadata(MigrationContext.configure(connection), m.metadata) == []
    snapshots["migrate"](storage, tmp_path / "repeat-upgrade")


def test_runtime_role_and_denied_ddl(db, storage):
    with transaction(db) as session:
        assert session.execute(text("SELECT current_user")).scalar_one() == storage.runtime_user
    for sql in [
        "CREATE TABLE forbidden_probe (id int)",
        "CREATE TEMP TABLE forbidden_probe (id int)",
        "CREATE ROLE forbidden_probe",
        "CREATE DATABASE forbidden_probe",
        "ALTER TABLE accounts ADD COLUMN probe int",
        "TRUNCATE TABLE audit_history",
        "DELETE FROM audit_history",
    ]:
        with pytest.raises(StorageError), transaction(db) as session:
            session.execute(text(sql))
    admin = engine_for(storage, admin=True)
    try:
        with pytest.raises(StorageError), transaction(admin):
            pass
    finally:
        admin.dispose()


def test_account_identity_and_company_candidates(db, account_id):
    subject = uuid4().hex
    with transaction(db) as session:
        session.execute(
            insert(m.accounts).values(
                id=uuid4(), provider="fixture", subject=subject, owner_subject="fixture-owner"
            )
        )
        ids = [create_record(session, account_id, "company") for _ in range(2)]
        for identity in ids:
            append_revision(
                session, identity, {"name": "Shared", "domain": "same.example"}, uuid4().hex
            )
        session.execute(
            insert(m.companies),
            [dict(id=i, account_id=account_id, name="Shared", domain="same.example") for i in ids],
        )
    with pytest.raises(StorageError), transaction(db) as session:
        session.execute(
            insert(m.accounts).values(
                id=uuid4(), provider="fixture", subject=subject, owner_subject="fixture-owner"
            )
        )
    with pytest.raises(StorageError), transaction(db) as session:
        session.execute(
            insert(m.companies).values(id=uuid4(), account_id=account_id, name="orphan")
        )


def test_run_generation_and_cross_account_rejection(db, account_id):
    with transaction(db) as session:
        identity = create_run(session, account_id, "research", uuid4().hex, "r1")
        assert (
            create_run(
                session,
                account_id,
                "research",
                session.execute(
                    select(m.runs.c.logical_key).where(m.runs.c.id == identity)
                ).scalar_one(),
                "r1",
            )
            == identity
        )
        transition_run(session, identity, "queued", 0, "canceled")
        successor = retry_run(session, identity, uuid4().hex)
        assert successor != identity
    with pytest.raises(StorageError), transaction(db) as session:
        session.execute(
            insert(m.runs).values(
                id=uuid4(),
                account_id=account_id,
                workflow_kind="changed",
                logical_key=uuid4().hex,
                input_revision="r2",
                execution_generation=1,
                predecessor_id=identity,
                retry_submission_key=uuid4().hex,
            )
        )


def test_raw_constraint_failures_rollback(db, account_id):
    with transaction(db) as session:
        identity = create_record(session, account_id, "contact")
        append_revision(session, identity, {"address": "same@example.test"}, uuid4().hex)
        session.execute(
            insert(m.contacts).values(
                id=identity,
                account_id=account_id,
                address="same@example.test",
                address_key="same@example.test",
            )
        )
    for address in ["same@example.test", "invalid"]:
        with pytest.raises(StorageError), transaction(db) as session:
            other = create_record(session, account_id, "contact")
            session.execute(
                insert(m.contacts).values(
                    id=other, account_id=account_id, address=address, address_key=address
                )
            )
    with transaction(db) as session:
        assert (
            session.execute(select(m.records.c.id).where(m.records.c.id == other)).first() is None
        )


def test_canonical_sql_requires_revision_and_outbox(db, account_id):
    from email_assistant.domain.states import content_hash

    with transaction(db) as session:
        identity = create_record(session, account_id, "company")
        append_revision(session, identity, {"name": "Original"}, "original")
        session.execute(
            insert(m.companies).values(id=identity, account_id=account_id, name="Original")
        )
    with pytest.raises(StorageError), transaction(db) as session:
        session.execute(
            update(m.companies).where(m.companies.c.id == identity).values(name="Unversioned")
        )
    with pytest.raises(StorageError), transaction(db) as session:
        session.execute(
            insert(m.revisions).values(
                id=uuid4(),
                account_id=account_id,
                record_id=identity,
                revision=2,
                submission_key="orphan",
                payload={"name": "Orphan"},
                content_hash=content_hash({"name": "Orphan"}),
            )
        )
    with transaction(db) as session:
        assert (
            session.execute(
                select(m.companies.c.name).where(m.companies.c.id == identity)
            ).scalar_one()
            == "Original"
        )
        assert append_revision(session, identity, {"name": "Versioned"}, "versioned") == 2
        session.execute(
            update(m.companies).where(m.companies.c.id == identity).values(name="Versioned")
        )


def test_membership_identifiers_and_account_boundaries(db, account_id):
    with transaction(db) as session:
        company, contact, source = [
            create_record(session, account_id, kind) for kind in ("company", "contact", "source")
        ]
        for identity in (company, contact, source):
            append_revision(session, identity, {}, uuid4().hex)
        session.execute(
            insert(m.companies).values(id=company, account_id=account_id, name="Fixture")
        )
        session.execute(
            insert(m.contacts).values(
                id=contact,
                account_id=account_id,
                address="shared@example.test",
                address_key="shared@example.test",
            )
        )
        session.execute(
            insert(m.sources).values(
                id=source,
                account_id=account_id,
                provider="fixture",
                source_type="document",
                external_key=uuid4().hex,
            )
        )
        membership = dict(company_id=company, contact_id=contact, account_id=account_id)
        identifier = dict(
            company_id=company,
            account_id=account_id,
            kind="domain",
            normalized_value="example.test",
            source_id=source,
            observed_at=datetime.now(UTC),
        )
        session.execute(insert(m.company_contacts).values(**membership))
        session.execute(insert(m.company_identifiers).values(id=uuid4(), **identifier))
        other_account = uuid4()
        session.execute(
            insert(m.accounts).values(
                id=other_account,
                provider="fixture",
                subject=uuid4().hex,
                owner_subject="fixture-owner",
            )
        )
        other_contact = create_record(session, other_account, "contact")
        append_revision(session, other_contact, {}, uuid4().hex)
        session.execute(
            insert(m.contacts).values(
                id=other_contact,
                account_id=other_account,
                address="shared@example.test",
                address_key="shared@example.test",
            )
        )
    for table, values in (
        (m.company_contacts, membership),
        (m.company_identifiers, dict(id=uuid4(), **identifier)),
        (m.company_contacts, dict(membership, contact_id=other_contact)),
        (m.company_identifiers, dict(identifier, id=uuid4(), account_id=other_account)),
    ):
        with pytest.raises(StorageError), transaction(db) as session:
            append_revision(session, company, {}, uuid4().hex)
            session.execute(insert(table).values(**values))


def test_one_active_gmail_retains_disconnected_history(db):
    first, second = uuid4(), uuid4()
    with transaction(db) as session:
        session.execute(
            insert(m.accounts).values(
                id=first, provider="gmail", subject=uuid4().hex, owner_subject="fixture-owner"
            )
        )
    with pytest.raises(StorageError), transaction(db) as session:
        session.execute(
            insert(m.accounts).values(
                id=second, provider="gmail", subject=uuid4().hex, owner_subject="fixture-owner"
            )
        )
    with transaction(db) as session:
        session.execute(
            update(m.accounts).where(m.accounts.c.id == first).values(state="disconnected")
        )
        session.execute(
            insert(m.accounts).values(
                id=second, provider="gmail", subject=uuid4().hex, owner_subject="fixture-owner"
            )
        )
        assert set(
            session.execute(
                select(m.accounts.c.state).where(m.accounts.c.id.in_([first, second]))
            ).scalars()
        ) == {"active", "disconnected"}


def test_raw_duplicate_workflow_and_action_keys(db, account_id):
    from email_assistant.persistence.workflows import create_action

    key = uuid4().hex
    with transaction(db) as session:
        create_run(session, account_id, "fixture", key, "r1")
        create_action(
            session, account_id, "send_reply", key, {}, ["recipient@example.test"], [], "r1"
        )
    with pytest.raises(StorageError), transaction(db) as session:
        session.execute(
            insert(m.runs).values(
                id=uuid4(),
                account_id=account_id,
                workflow_kind="fixture",
                logical_key=key,
                input_revision="r1",
            )
        )
    with pytest.raises(StorageError), transaction(db) as session:
        identity = create_record(session, account_id, "action")
        session.execute(
            insert(m.actions).values(
                id=identity,
                account_id=account_id,
                kind="send_reply",
                logical_key=key,
                current_revision=1,
            )
        )


def test_database_errors_do_not_expose_parameters(db, caplog):
    private = "permitted-synthetic-private-parameter"
    with pytest.raises(StorageError) as error, transaction(db) as session:
        session.execute(text("SELECT CAST(:private AS integer)"), {"private": private})
    assert private not in str(error.value) + caplog.text
