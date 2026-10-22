"""Canonical revisions and independent projection bookkeeping; no projector execution."""

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session

from email_assistant.domain.states import content_hash
from email_assistant.models import records as m
from email_assistant.persistence.database import Conflict


def create_record(session: Session, account_id: UUID, record_type: str) -> UUID:
    identity = uuid4()
    session.execute(
        insert(m.records).values(id=identity, account_id=account_id, record_type=record_type)
    )
    return identity


def append_revision(
    session: Session,
    identity: UUID,
    payload: dict[str, Any],
    submission_key: str,
    *,
    deleted: bool = False,
) -> int:
    if not isinstance(payload, dict) or not submission_key.strip():
        raise ValueError("Versioned object payload and submission key required")
    row = (
        session.execute(select(m.records).where(m.records.c.id == identity).with_for_update())
        .mappings()
        .one()
    )
    digest = content_hash(payload)
    old = (
        session.execute(
            select(m.revisions).where(
                m.revisions.c.record_id == identity, m.revisions.c.submission_key == submission_key
            )
        )
        .mappings()
        .one_or_none()
    )
    if old:
        operation = session.execute(
            select(m.outbox.c.operation).where(
                m.outbox.c.entity_id == identity, m.outbox.c.revision == old.revision
            )
        ).scalar_one()
        if old.content_hash != digest or (operation == "delete") != deleted:
            raise Conflict("Revision submission differs")
        return int(old.revision)
    if row.deleted:
        raise Conflict("Deleted canonical record cannot be resurrected")
    revision = row.revision + 1
    session.execute(
        insert(m.revisions).values(
            id=uuid4(),
            record_id=identity,
            account_id=row.account_id,
            revision=revision,
            submission_key=submission_key,
            payload_version=1,
            payload=payload,
            content_hash=digest,
        )
    )
    session.execute(
        update(m.records)
        .where(m.records.c.id == identity)
        .values(revision=revision, deleted=deleted)
    )
    event_id = uuid4()
    session.execute(
        insert(m.outbox).values(
            id=event_id,
            account_id=row.account_id,
            entity_id=identity,
            entity_type=row.record_type,
            revision=revision,
            operation="delete" if deleted else "upsert",
        )
    )
    session.execute(
        insert(m.projection_deliveries),
        [{"event_id": event_id, "target": target} for target in ("neo4j", "qdrant")],
    )
    return int(revision)


def acknowledge(session: Session, event_id: UUID, target: str, version: int) -> int:
    if target not in {"neo4j", "qdrant"}:
        raise ValueError("Unknown projection target")
    event = session.execute(select(m.outbox).where(m.outbox.c.id == event_id)).mappings().one()
    session.execute(
        select(m.records.c.id).where(m.records.c.id == event.entity_id).with_for_update()
    ).one()
    delivery = (
        session.execute(
            select(m.projection_deliveries)
            .where(
                m.projection_deliveries.c.event_id == event_id,
                m.projection_deliveries.c.target == target,
            )
            .with_for_update()
        )
        .mappings()
        .one()
    )
    if delivery.state == "applied":
        return int(delivery.version)
    if delivery.version != version:
        raise Conflict("Stale projection delivery version")
    checkpoint = (
        session.execute(
            select(m.projection_checkpoints).where(
                m.projection_checkpoints.c.entity_id == event.entity_id,
                m.projection_checkpoints.c.target == target,
            )
        )
        .mappings()
        .one_or_none()
    )
    if checkpoint and checkpoint.revision >= event.revision:
        raise Conflict("Stale event cannot advance checkpoint")
    values = {"revision": event.revision, "deleted": event.operation == "delete"}
    if checkpoint:
        session.execute(
            update(m.projection_checkpoints)
            .where(
                m.projection_checkpoints.c.entity_id == event.entity_id,
                m.projection_checkpoints.c.target == target,
            )
            .values(**values, version=checkpoint.version + 1)
        )
    else:
        session.execute(
            insert(m.projection_checkpoints).values(
                entity_id=event.entity_id, target=target, **values
            )
        )
    session.execute(
        update(m.projection_deliveries)
        .where(
            m.projection_deliveries.c.event_id == event_id,
            m.projection_deliveries.c.target == target,
        )
        .values(
            state="applied",
            version=version + 1,
            attempts=delivery.attempts + 1,
            retry_at=None,
            failure_code=None,
        )
    )
    return version + 1
