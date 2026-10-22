"""Transactional storage operations. Call inside database.transaction()."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session

from email_assistant.domain.states import ACTION_EDGES, RUN_EDGES, content_hash, validate_snapshot
from email_assistant.models import records as m
from email_assistant.persistence.database import Conflict


def locked(session: Session, table: Any, identity: UUID) -> Any:
    row = (
        session.execute(select(table).where(table.c.id == identity).with_for_update())
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise Conflict("Record missing")
    return row


def create_run(
    session: Session, account_id: UUID, kind: str, logical_key: str, input_revision: str
) -> UUID:
    if not all(isinstance(v, str) and v.strip() for v in (kind, logical_key, input_revision)):
        raise ValueError("Run identity required")
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    identity = uuid4()
    session.execute(
        pg_insert(m.runs)
        .values(
            id=identity,
            account_id=account_id,
            workflow_kind=kind,
            logical_key=logical_key,
            input_revision=input_revision,
        )
        .on_conflict_do_nothing()
    )
    return cast(
        UUID,
        session.execute(
            select(m.runs.c.id).where(
                m.runs.c.account_id == account_id,
                m.runs.c.workflow_kind == kind,
                m.runs.c.logical_key == logical_key,
                m.runs.c.input_revision == input_revision,
                m.runs.c.execution_generation == 0,
            )
        ).scalar_one(),
    )


def transition_run(
    session: Session, identity: UUID, expected: str, version: int, target: str
) -> int:
    if target not in RUN_EDGES.get(expected, set()):
        raise Conflict("Invalid run transition")
    result = session.execute(
        update(m.runs)
        .where(m.runs.c.id == identity, m.runs.c.state == expected, m.runs.c.version == version)
        .values(state=target, version=version + 1)
        .returning(m.runs.c.version)
    ).scalar_one_or_none()
    if result is None:
        raise Conflict("Stale run state/version")
    return int(result)


def retry_run(session: Session, predecessor: UUID, submission_key: str) -> UUID:
    if not submission_key.strip():
        raise ValueError("Retry submission key required")
    row = locked(session, m.runs, predecessor)
    existing = (
        session.execute(
            select(m.runs).where(
                m.runs.c.account_id == row.account_id,
                m.runs.c.retry_submission_key == submission_key,
            )
        )
        .mappings()
        .one_or_none()
    )
    if existing:
        if existing.predecessor_id != predecessor:
            raise Conflict("Retry submission reused for different input")
        return cast(UUID, existing.id)
    if RUN_EDGES[row.state] or row.state == "awaiting_owner":
        raise Conflict("Only terminal runs can be retried")
    if session.execute(select(m.runs.c.id).where(m.runs.c.predecessor_id == predecessor)).first():
        raise Conflict("Predecessor already has successor")
    identity = uuid4()
    session.execute(
        insert(m.runs).values(
            id=identity,
            account_id=row.account_id,
            workflow_kind=row.workflow_kind,
            logical_key=row.logical_key,
            input_revision=row.input_revision,
            execution_generation=row.execution_generation + 1,
            predecessor_id=predecessor,
            retry_submission_key=submission_key,
        )
    )
    return identity


def save_step(
    session: Session,
    run_id: UUID,
    key: str,
    input_revision: str,
    input_ref: str,
    output_ref: str | None = None,
) -> UUID:
    parent = locked(session, m.runs, run_id)
    if parent.input_revision != input_revision or parent.state != "running":
        raise Conflict("Step input/run not eligible")
    existing = (
        session.execute(
            select(m.run_steps)
            .where(
                m.run_steps.c.run_id == run_id,
                m.run_steps.c.step_key == key,
                m.run_steps.c.input_revision == input_revision,
            )
            .with_for_update()
        )
        .mappings()
        .one_or_none()
    )
    if existing:
        if existing.input_ref != input_ref or (
            existing.state == "completed" and existing.output_ref != output_ref
        ):
            raise Conflict("Step input/output mismatch")
        if existing.state != "completed" and output_ref is not None:
            session.execute(
                update(m.run_steps)
                .where(m.run_steps.c.id == existing.id)
                .values(state="completed", output_ref=output_ref)
            )
        return cast(UUID, existing.id)
    identity = uuid4()
    session.execute(
        insert(m.run_steps).values(
            id=identity,
            run_id=run_id,
            step_key=key,
            input_revision=input_revision,
            input_ref=input_ref,
            output_ref=output_ref,
            state="completed" if output_ref is not None else "pending",
        )
    )
    return identity


def pending_steps(session: Session, run_id: UUID) -> list[Any]:
    return list(
        session.execute(
            select(m.run_steps)
            .join(m.runs)
            .where(
                m.runs.c.id == run_id,
                m.runs.c.state == "running",
                m.run_steps.c.input_revision == m.runs.c.input_revision,
                m.run_steps.c.state != "completed",
            )
        ).mappings()
    )


def create_action(
    session: Session,
    account_id: UUID,
    kind: str,
    logical_key: str,
    payload: dict[str, Any],
    destinations: list[str],
    attachments: list[dict[str, str]],
    submission_key: str,
) -> UUID:
    validate_snapshot(kind, destinations, attachments)
    # Serialize first creation for one account; subsequent operations lock the action.
    locked(session, m.accounts, account_id)
    existing = (
        session.execute(
            select(m.actions).where(
                m.actions.c.account_id == account_id,
                m.actions.c.kind == kind,
                m.actions.c.logical_key == logical_key,
            )
        )
        .mappings()
        .one_or_none()
    )
    if existing:
        revision = (
            session.execute(
                select(m.revisions).where(
                    m.revisions.c.record_id == existing.id,
                    m.revisions.c.submission_key == submission_key,
                )
            )
            .mappings()
            .one_or_none()
        )
        snapshot = {
            "content": payload,
            "kind": kind,
            "destinations": destinations,
            "attachments": attachments,
        }
        if revision is None or revision.content_hash != content_hash(snapshot):
            raise Conflict("Logical action already exists with different submission")
        return cast(UUID, existing.id)
    identity = uuid4()
    session.execute(
        insert(m.records).values(id=identity, account_id=account_id, record_type="action")
    )
    session.execute(
        insert(m.actions).values(
            id=identity,
            account_id=account_id,
            kind=kind,
            logical_key=logical_key,
            current_revision=1,
        )
    )
    _append_action_revision(
        session, identity, account_id, kind, 1, payload, destinations, attachments, submission_key
    )
    return identity


def _append_action_revision(
    session: Session,
    identity: UUID,
    account_id: UUID,
    kind: str,
    revision: int,
    payload: dict[str, Any],
    destinations: list[str],
    attachments: list[dict[str, str]],
    submission_key: str,
) -> None:
    from email_assistant.persistence.projections import append_revision

    append_revision(
        session,
        identity,
        {
            "content": payload,
            "kind": kind,
            "destinations": destinations,
            "attachments": attachments,
        },
        submission_key,
    )
    session.execute(
        insert(m.action_revisions).values(
            action_id=identity,
            account_id=account_id,
            revision=revision,
            kind=kind,
            destinations=destinations,
            attachments=attachments,
        )
    )


def edit_action(
    session: Session,
    identity: UUID,
    version: int,
    payload: dict[str, Any],
    destinations: list[str],
    attachments: list[dict[str, str]],
    submission_key: str,
) -> int:
    row = locked(session, m.actions, identity)
    validate_snapshot(row.kind, destinations, attachments)
    snapshot = {
        "content": payload,
        "kind": row.kind,
        "destinations": destinations,
        "attachments": attachments,
    }
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
        if old.content_hash != content_hash(snapshot):
            raise Conflict("Revision submission payload differs")
        return int(old.revision)
    if row.version != version or row.state in {"claimed", "unknown", "succeeded"}:
        raise Conflict("Stale or locked action")
    revision = row.current_revision + 1
    _append_action_revision(
        session,
        identity,
        row.account_id,
        row.kind,
        revision,
        payload,
        destinations,
        attachments,
        submission_key,
    )
    session.execute(
        update(m.actions)
        .where(m.actions.c.id == identity)
        .values(current_revision=revision, state="draft", version=version + 1, evidence_id=None)
    )
    return int(revision)


def transition_action(
    session: Session,
    identity: UUID,
    expected: str,
    version: int,
    target: str,
    evidence_id: UUID | None = None,
) -> int:
    if target not in ACTION_EDGES.get(expected, set()):
        raise Conflict("Invalid action transition")
    values: dict[str, Any] = {"state": target, "version": version + 1}
    if evidence_id is not None:
        values["evidence_id"] = evidence_id
    result = session.execute(
        update(m.actions)
        .where(
            m.actions.c.id == identity,
            m.actions.c.state == expected,
            m.actions.c.version == version,
        )
        .values(**values)
        .returning(m.actions.c.version)
    ).scalar_one_or_none()
    if result is None:
        raise Conflict("Stale action state/version")
    return int(result)


def decide(
    session: Session,
    identity: UUID,
    version: int,
    revision: int,
    actor_ref: str,
    decision: str,
    submission_key: str,
) -> UUID:
    """actor_ref MUST come from #19's authenticated boundary, never model/client claims."""
    row = locked(session, m.actions, identity)
    existing = (
        session.execute(
            select(m.approvals).where(
                m.approvals.c.account_id == row.account_id,
                m.approvals.c.submission_key == submission_key,
            )
        )
        .mappings()
        .one_or_none()
    )
    if existing:
        if (existing.action_id, existing.revision, existing.actor_ref, existing.decision) != (
            identity,
            revision,
            actor_ref,
            decision,
        ):
            raise Conflict("Decision submission differs")
        return cast(UUID, existing.id)
    if (
        row.version != version
        or row.current_revision != revision
        or row.state != "awaiting_approval"
    ):
        raise Conflict("Stale decision")
    if decision not in {"approved", "rejected"}:
        raise ValueError("Invalid decision")
    result = uuid4()
    session.execute(
        insert(m.approvals).values(
            id=result,
            account_id=row.account_id,
            action_id=identity,
            revision=revision,
            actor_ref=actor_ref,
            decision=decision,
            submission_key=submission_key,
        )
    )
    transition_action(
        session,
        identity,
        "awaiting_approval",
        version,
        "approved" if decision == "approved" else "draft",
    )
    return result


def claim(
    session: Session, identity: UUID, version: int, lease_seconds: int = 60
) -> dict[str, Any]:
    if not 1 <= lease_seconds <= 3600:
        raise ValueError("Lease must be 1..3600 seconds")
    row = locked(session, m.actions, identity)
    if row.state != "approved" or row.version != version:
        raise Conflict("Stale or unapproved claim")
    # Validate attachment readiness/deletion again, immediately before claiming.
    snapshot = (
        session.execute(
            select(m.action_revisions).where(
                m.action_revisions.c.action_id == identity,
                m.action_revisions.c.revision == row.current_revision,
            )
        )
        .mappings()
        .one()
    )
    for item in snapshot.attachments:
        artifact = locked(session, m.artifacts, UUID(item["id"]))
        if artifact.state != "ready" or artifact.deleted_at or artifact.checksum != item["hash"]:
            raise Conflict("Attachment no longer valid")
    now = datetime.now(UTC)
    attempt = {
        "id": uuid4(),
        "account_id": row.account_id,
        "action_id": identity,
        "revision": row.current_revision,
        "attempt_number": row.fence + 1,
        "claim_token": uuid4(),
        "fence": row.fence + 1,
        "started_at": now,
        "heartbeat_at": now,
        "lease_until": now + timedelta(seconds=lease_seconds),
    }
    session.execute(
        update(m.actions)
        .where(m.actions.c.id == identity)
        .values(state="claimed", version=version + 1, fence=row.fence + 1)
    )
    session.execute(insert(m.action_attempts).values(**attempt))
    return attempt


def finish(
    session: Session,
    identity: UUID,
    version: int,
    token: UUID,
    fence: int,
    result: str,
    *,
    provider_id: str | None = None,
    failure_code: str | None = None,
    expired: bool = False,
) -> int:
    row = locked(session, m.actions, identity)
    attempt = (
        session.execute(
            select(m.action_attempts)
            .where(
                m.action_attempts.c.action_id == identity,
                m.action_attempts.c.claim_token == token,
                m.action_attempts.c.fence == fence,
                m.action_attempts.c.finished_at.is_(None),
            )
            .with_for_update()
        )
        .mappings()
        .one_or_none()
    )
    if row.version != version or row.state != "claimed" or row.fence != fence or attempt is None:
        raise Conflict("Stale claim fence/token/version")
    now = datetime.now(UTC)
    if result not in {"succeeded", "failed_known", "unknown"}:
        raise ValueError("Invalid outcome")
    if failure_code is not None:
        import re

        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", failure_code):
            raise ValueError("Sanitized failure code required")
    if expired and (attempt.lease_until > now or result != "unknown"):
        raise Conflict("Expiry permits only unknown")
    if not expired and attempt.lease_until <= now and result != "unknown":
        raise Conflict("Expired claim requires unknown")
    session.execute(
        update(m.action_attempts)
        .where(m.action_attempts.c.id == attempt.id)
        .values(result=result, finished_at=now, provider_id=provider_id, failure_code=failure_code)
    )
    return transition_action(session, identity, "claimed", version, result)


def record_evidence(
    session: Session, identity: UUID, revision: int, kind: str, reference: str, actor_ref: str
) -> UUID:
    row = locked(session, m.actions, identity)
    if row.current_revision != revision or not reference.strip() or not actor_ref.strip():
        raise Conflict("Evidence revision/reference required")
    result = uuid4()
    session.execute(
        insert(m.action_evidence).values(
            id=result,
            account_id=row.account_id,
            action_id=identity,
            revision=revision,
            kind=kind,
            reference=reference,
            actor_ref=actor_ref,
        )
    )
    return result
