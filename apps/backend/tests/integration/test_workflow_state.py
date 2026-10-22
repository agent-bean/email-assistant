from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import insert, select, update

from email_assistant.domain.states import ACTION_EDGES, RUN_EDGES
from email_assistant.models import records as m
from email_assistant.persistence import workflows as w
from email_assistant.persistence.database import Conflict, StorageError, transaction

pytestmark = pytest.mark.integration


def action(db, account_id, state="draft"):
    with transaction(db) as session:
        identity = w.create_action(
            session,
            account_id,
            "send_reply",
            uuid4().hex,
            {"body": "permitted synthetic reply"},
            ["recipient@example.test"],
            [],
            uuid4().hex,
        )
        if state != "draft":
            w.transition_action(session, identity, "draft", 0, "awaiting_approval")
        if state in {"approved", "claimed", "unknown", "failed_known", "succeeded"}:
            w.decide(session, identity, 1, 1, "fixture-owner", "approved", uuid4().hex)
        attempt = None
        if state in {"claimed", "unknown", "failed_known", "succeeded"}:
            attempt = w.claim(session, identity, 2)
        if state in {"unknown", "failed_known", "succeeded"}:
            w.finish(session, identity, 3, attempt["claim_token"], attempt["fence"], state)
    return identity, attempt


def race(db, first, second):
    barrier = Barrier(2)

    def run(operation):
        try:
            with transaction(db) as session:
                barrier.wait(timeout=10)
                return operation(session)
        except Conflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        a = executor.submit(run, first)
        b = executor.submit(run, second)
        return [a.result(timeout=20), b.result(timeout=20)]


def test_run_and_action_invalid_edge_matrix(db, account_id):
    for initial in RUN_EDGES:
        for target in RUN_EDGES:
            if target in RUN_EDGES[initial]:
                continue
            with transaction(db) as session:
                identity = w.create_run(session, account_id, "fixture", uuid4().hex, "r1")
                version = 0
                if initial != "queued":
                    version = w.transition_run(session, identity, "queued", 0, "running")
                    if initial != "running":
                        version = w.transition_run(session, identity, "running", 1, initial)
            with pytest.raises(StorageError), transaction(db) as session:
                session.execute(
                    update(m.runs)
                    .where(m.runs.c.id == identity)
                    .values(state=target, version=version + 1)
                )
    for initial in ACTION_EDGES:
        identity, _ = action(db, account_id, initial)
        for target in ACTION_EDGES:
            if target in ACTION_EDGES[initial]:
                continue
            with pytest.raises(StorageError), transaction(db) as session:
                session.execute(
                    update(m.actions)
                    .where(m.actions.c.id == identity)
                    .values(state=target, version=m.actions.c.version + 1)
                )


def test_concurrent_claim_decision_edit_and_retry(db, account_id):
    identity, _ = action(db, account_id, "approved")
    results = race(db, lambda s: w.claim(s, identity, 2), lambda s: w.claim(s, identity, 2))
    assert results.count("conflict") == 1
    with transaction(db) as session:
        assert (
            len(
                list(
                    session.execute(
                        select(m.action_attempts).where(m.action_attempts.c.action_id == identity)
                    )
                )
            )
            == 1
        )
    identity, _ = action(db, account_id, "approved")
    results = race(
        db,
        lambda s: w.claim(s, identity, 2),
        lambda s: w.edit_action(
            s, identity, 2, {"body": "changed"}, ["recipient@example.test"], [], uuid4().hex
        ),
    )
    assert results.count("conflict") == 1
    identity, _ = action(db, account_id, "awaiting_approval")
    key = uuid4().hex
    results = race(
        db,
        lambda s: w.decide(s, identity, 1, 1, "fixture-owner", "approved", key),
        lambda s: w.decide(s, identity, 1, 1, "fixture-owner", "approved", key),
    )
    assert results[0] == results[1] and results[0] != "conflict"
    with transaction(db) as session:
        run = w.create_run(session, account_id, "fixture", uuid4().hex, "r1")
        w.transition_run(session, run, "queued", 0, "canceled")
    key = uuid4().hex
    results = race(db, lambda s: w.retry_run(s, run, key), lambda s: w.retry_run(s, run, key))
    assert results[0] == results[1] and results[0] != "conflict"


def test_revision_history_rejection_and_atomic_rollback(db, account_id):
    identity, _ = action(db, account_id, "approved")
    with transaction(db) as session:
        w.edit_action(session, identity, 2, {"body": "B"}, ["recipient@example.test"], [], "b")
        w.edit_action(
            session,
            identity,
            3,
            {"body": "permitted synthetic reply"},
            ["recipient@example.test"],
            [],
            "a-again",
        )
        hashes = (
            session.execute(
                select(m.revisions.c.content_hash)
                .where(m.revisions.c.record_id == identity)
                .order_by(m.revisions.c.revision)
            )
            .scalars()
            .all()
        )
        assert hashes[0] == hashes[2] != hashes[1]
        w.transition_action(session, identity, "draft", 4, "awaiting_approval")
    with pytest.raises(Conflict), transaction(db) as session:
        w.decide(session, identity, 5, 3, "fixture-owner", "approved", "rollback")
        raise Conflict("force rollback after multirow writes")
    with transaction(db) as session:
        assert (
            session.execute(
                select(m.approvals).where(
                    m.approvals.c.action_id == identity, m.approvals.c.revision == 3
                )
            ).first()
            is None
        )
        assert (
            session.execute(
                select(m.actions.c.state).where(m.actions.c.id == identity)
            ).scalar_one()
            == "awaiting_approval"
        )
        w.decide(session, identity, 5, 3, "fixture-owner", "rejected", "rejection")
    with pytest.raises(StorageError), transaction(db) as session:
        session.execute(
            update(m.revisions)
            .where(m.revisions.c.record_id == identity)
            .values(content_hash="0" * 64)
        )
    with pytest.raises(StorageError), transaction(db) as session:
        session.execute(
            update(m.approvals)
            .where(m.approvals.c.action_id == identity)
            .values(actor_ref="different")
        )


def test_unknown_fence_and_expiry(db, account_id, monkeypatch):
    identity, attempt = action(db, account_id, "claimed")
    for bad_token, bad_fence in [(uuid4(), attempt["fence"]), (attempt["claim_token"], 999)]:
        with pytest.raises(Conflict), transaction(db) as session:
            w.finish(session, identity, 3, bad_token, bad_fence, "succeeded")
    with transaction(db) as session:
        w.finish(session, identity, 3, attempt["claim_token"], attempt["fence"], "unknown")
    for state in ["approved", "claimed", "draft"]:
        with pytest.raises(Conflict), transaction(db) as session:
            w.transition_action(session, identity, "unknown", 4, state)
    with pytest.raises(StorageError), transaction(db) as session:
        w.transition_action(session, identity, "unknown", 4, "failed_known")
    with transaction(db) as session:
        evidence = w.record_evidence(
            session, identity, 1, "resolution", "fixture-proof", "fixture-owner"
        )
        w.transition_action(session, identity, "unknown", 4, "failed_known", evidence)
        evidence = w.record_evidence(
            session, identity, 1, "safe_retry", "fixture-no-effect", "fixture-owner"
        )
        w.transition_action(session, identity, "failed_known", 5, "approved", evidence)
        w.claim(session, identity, 6)
    identity, _ = action(db, account_id, "approved")

    class Past(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(UTC) - timedelta(minutes=2)

    with monkeypatch.context() as patch:
        patch.setattr(w, "datetime", Past)
        with transaction(db) as session:
            attempt = w.claim(session, identity, 2, lease_seconds=60)
    with transaction(db) as session:
        w.finish(
            session, identity, 3, attempt["claim_token"], attempt["fence"], "unknown", expired=True
        )
    with pytest.raises(Conflict), transaction(db) as session:
        w.edit_action(session, identity, 4, {}, ["x@example.test"], [], "locked")


def test_completed_steps_survive_fresh_sessions(db, account_id):
    with transaction(db) as session:
        run = w.create_run(session, account_id, "research", uuid4().hex, "r1")
        w.transition_run(session, run, "queued", 0, "running")
        w.save_step(session, run, "done", "r1", "input:1", "output:1")
        w.save_step(session, run, "todo", "r1", "input:2")
    with transaction(db) as session:
        assert [row.step_key for row in w.pending_steps(session, run)] == ["todo"]
    with pytest.raises(StorageError), transaction(db) as session:
        session.execute(
            update(m.run_steps)
            .where(m.run_steps.c.run_id == run, m.run_steps.c.step_key == "done")
            .values(output_ref="changed")
        )


@pytest.mark.parametrize(
    "changed",
    [
        {"kind": "forward_report"},
        {"destinations": ["other@example.test"]},
        {"attachments": [{"id": str(uuid4()), "hash": "0" * 64}]},
    ],
)
def test_sql_snapshot_must_match_canonical_revision(db, account_id, changed):
    from email_assistant.persistence.projections import append_revision, create_record

    with pytest.raises(StorageError), transaction(db) as session:
        identity = create_record(session, account_id, "action")
        session.execute(
            insert(m.actions).values(
                id=identity,
                account_id=account_id,
                kind="send_reply",
                logical_key=uuid4().hex,
                current_revision=1,
            )
        )
        snapshot = dict(kind="send_reply", destinations=["recipient@example.test"], attachments=[])
        append_revision(session, identity, dict(content={}, **snapshot), uuid4().hex)
        session.execute(
            insert(m.action_revisions).values(
                action_id=identity, account_id=account_id, revision=1, **dict(snapshot, **changed)
            )
        )
