from uuid import uuid4

import pytest
from sqlalchemy import insert, select, update

from email_assistant.models import records as m
from email_assistant.persistence.database import Conflict, StorageError, transaction
from email_assistant.persistence.projections import acknowledge, append_revision, create_record

pytestmark = pytest.mark.integration


def test_atomic_outbox_tombstones_and_independent_targets(db, account_id):
    with transaction(db) as session:
        identity = create_record(session, account_id, "report")
        assert append_revision(session, identity, {"text": "A"}, "one") == 1
        assert append_revision(session, identity, {"text": "A"}, "one") == 1
        append_revision(session, identity, {"text": "B"}, "two")
        append_revision(session, identity, {"text": "A"}, "three")
        append_revision(session, identity, {}, "delete", deleted=True)
    with transaction(db) as session:
        events = (
            session.execute(
                select(m.outbox)
                .where(m.outbox.c.entity_id == identity)
                .order_by(m.outbox.c.revision)
            )
            .mappings()
            .all()
        )
        assert len(events) == 4
        assert acknowledge(session, events[1].id, "neo4j", 0) == 1
        assert acknowledge(session, events[1].id, "neo4j", 0) == 1
        assert acknowledge(session, events[3].id, "qdrant", 0) == 1
    for index, target in [(0, "neo4j"), (2, "qdrant")]:
        with pytest.raises(Conflict), transaction(db) as session:
            acknowledge(session, events[index].id, target, 0)
    with pytest.raises(Conflict), transaction(db) as session:
        append_revision(session, identity, {"text": "resurrect"}, "late")
    with transaction(db) as session:
        rows = (
            session.execute(
                select(m.projection_checkpoints).where(
                    m.projection_checkpoints.c.entity_id == identity
                )
            )
            .mappings()
            .all()
        )
        assert {(r.target, r.revision, r.deleted) for r in rows} == {
            ("neo4j", 2, False),
            ("qdrant", 4, True),
        }
    with pytest.raises(Conflict), transaction(db) as session:
        failed = create_record(session, account_id, "report")
        append_revision(session, failed, {}, "rollback")
        raise Conflict("after canonical/event creation")
    with transaction(db) as session:
        assert (
            session.execute(select(m.outbox).where(m.outbox.c.entity_id == failed)).first() is None
        )
        assert session.execute(select(m.records).where(m.records.c.id == failed)).first() is None


def test_sql_projection_bookkeeping_rejects_unapplied_and_rewound_state(db, account_id):
    with transaction(db) as session:
        identity = create_record(session, account_id, "report")
        append_revision(session, identity, {}, "first")
        event = session.execute(
            select(m.outbox.c.id).where(m.outbox.c.entity_id == identity)
        ).scalar_one()
    with pytest.raises(StorageError), transaction(db) as session:
        session.execute(
            insert(m.projection_checkpoints).values(
                entity_id=identity, target="neo4j", revision=1, deleted=False
            )
        )
    with pytest.raises(StorageError), transaction(db) as session:
        session.execute(
            update(m.projection_deliveries)
            .where(
                m.projection_deliveries.c.event_id == event,
                m.projection_deliveries.c.target == "neo4j",
            )
            .values(state="applied", version=1)
        )
    with transaction(db) as session:
        acknowledge(session, event, "neo4j", 0)
    with pytest.raises(StorageError), transaction(db) as session:
        session.execute(
            update(m.projection_deliveries)
            .where(
                m.projection_deliveries.c.event_id == event,
                m.projection_deliveries.c.target == "neo4j",
            )
            .values(state="pending", version=2)
        )


def test_embedding_generation_and_relationship_provenance(db, account_id):
    from email_assistant.persistence.artifacts import prepare

    with transaction(db) as session:
        source = create_record(session, account_id, "source")
        company = create_record(session, account_id, "company")
        report = create_record(session, account_id, "report")
        append_revision(session, source, {"url": "https://example.test"}, "source")
        append_revision(session, report, {"text": "permitted synthetic research"}, "report")
        session.execute(
            insert(m.relationships).values(
                id=uuid4(),
                account_id=account_id,
                record_id=report,
                source_revision=1,
                subject_id=company,
                object_id=report,
                predicate="has_report",
                evidence_id=source,
                evidence_revision=1,
                confirmed=False,
            )
        )
        generation = uuid4()
        session.execute(
            insert(m.index_generations).values(
                id=generation,
                provider="fixture",
                model="storage-only",
                model_version="1",
                dimension=2,
            )
        )
        artifact = prepare(
            session,
            account_id,
            "0" * 64,
            0,
            "application/octet-stream",
            "vector",
            "cached_vector",
            record_id=report,
            source_revision=1,
        )
    # A vector reference cannot lie about model/dimension or artifact account/hash.
    for dimension, checksum in [(3, "0" * 64), (2, "1" * 64)]:
        with pytest.raises(StorageError), transaction(db) as session:
            session.execute(
                insert(m.embedding_cache).values(
                    id=uuid4(),
                    account_id=account_id,
                    record_id=report,
                    source_revision=1,
                    chunk_key="chunk-1",
                    chunk_text="fixture",
                    generation_id=generation,
                    provider="fixture",
                    model="storage-only",
                    model_version="1",
                    dimension=dimension,
                    artifact_id=artifact,
                    artifact_hash=checksum,
                )
            )
