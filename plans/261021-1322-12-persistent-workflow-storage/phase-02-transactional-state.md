---
title: "Phase 2: Transactional workflow state"
status: todo
priority: P1
effort: 1-1.5d
---

# Phase 2: Transactional workflow state

## Context and outcome

Depends on phase 1. Read [blueprint state contract](../../docs/codebase-blueprint.md#state-ownership-and-recovery), [phase 1](./phase-01-start.md), and issues [#19](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/19), [#20](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/20). Deliver a persistence-level state machine with concurrency guards. Authenticated approval handlers and provider action execution remain downstream.

## Requirements and transition policy

Statuses must use exactly the blueprint vocabulary. State CHECK constraints alone cannot validate old-to-new edges. Use a database transition trigger/function plus state-version compare-and-swap in persistence operations. Enforce append-only revision/approval history against ordinary app operations. Document the privileged migration-role boundary; no claim of protection from a database administrator.

Validated run transitions:

| From | Allowed next |
|---|---|
| queued | running, canceled |
| running | awaiting_owner, succeeded, partial, failed, canceled |
| awaiting_owner | queued, canceled |
| succeeded, partial, failed, canceled | none; an explicit retry creates a new run linked to its predecessor |

Restart keeps a `running` record and resumes eligible unfinished steps by persisted input revision. It does not replay completed steps, mutate terminal states or start a worker in this issue. Storage only provides pending-work queries and durable checkpoints.

| Action from | Allowed next | Guard |
|---|---|---|
| draft | awaiting_approval | Complete immutable revision exists |
| awaiting_approval | approved, draft | Approved requires matching current owner decision; rejection returns draft |
| approved | claimed, draft | Claim rechecks exact revision approval transactionally; edit returns draft on new revision |
| claimed | succeeded, failed_known, unknown | Current claim token/fence; no provider replay |
| failed_known | approved, draft | Return to approved only for explicit safe-retry evidence and still-valid exact-revision approval; otherwise new revision returns draft. #20 owns proving retry eligibility |
| unknown | succeeded, failed_known | Explicit reconciliation/resolution evidence; never auto-claim or auto-retry |
| succeeded | none | Immutable terminal outcome |

A new action revision creates a new immutable row and invalidates old executable authorization without deleting approval history. Editing a claimed or unknown revision is refused; retain uncertain intent for #20 to reconcile. Succeeded actions stay unchanged; a distinct new logical action requires distinct intent. Approval, current revision, kind, exact destinations and attachment hashes must agree at claim. Different action kinds cannot share approval.

A failed_known action may reuse still-valid approval only for the identical immutable revision after #20 establishes no external effect; this transition never applies to unknown. Persist retry evidence and repeat all claim validity checks.

Claim/attempt creation uses a short transaction and monotonic fence/version. Unique live-claim constraint and row locking/CAS make two simultaneous attempts produce one winner. Store lease and heartbeat fields but do not implement a worker timer. Expiry of an external claimed action permits only recording `unknown`; it never grants retry. Do not represent safe read/research leases as external send actions.

## Files and ownership

- Create `apps/backend/src/email_assistant/domain/{__init__,states}.py`: explicit statuses, edges and validated input values, with no fake owner authentication.
- Create `apps/backend/src/email_assistant/persistence/workflows.py`: run/step operations, revision append, decision record, claim and outcome persistence. Keep transactions local; no generic unit-of-work framework.
- Extend `models/records.py`; create one ordered Alembic revision for transition/immutability guards and least-privilege app grants. Do not silently re-edit an already-applied revision.
- Create `apps/backend/tests/unit/test_states.py`, `tests/integration/test_workflow_state.py`. Extend migration/bootstrap logic only after phase 1 completes.

## Implementation steps

1. Write allowed/rejected edge matrix tests first. Keep logical input identity unchanged on retry; allocate next execution generation under predecessor lock with one successor and idempotent retry submission key. Store explicit predecessor link. Prove two simultaneous retry requests cannot create divergent successors. Validate state values and hashes/recipient snapshot shapes at persistence boundary.
2. Add SQL guards for invalid state edges, immutable approved revision payloads and invalid current-approval/action relationships. Ensure direct ordinary-role UPDATE cannot bypass these checks.
3. Separate migration/admin connection from a least-privilege runtime role in both local operator setup and disposable harness. Define distinct private connection settings, provision grants without exposing credentials and verify actual current_user, superuser/CREATEDB/CREATEROLE flags, object ownership and denied DDL before runtime writes. Grant only required access; protect history with DB guards. Keep private credential handling consistent with phase 1; document role creation and grants without printing credentials.
4. Implement CAS by ID, expected state and version; return one typed conflict for zero affected rows, with no partial audit/attempt write. Use row locks where claim checks span multiple rows; serialize concurrent edit/decision/claim on the parent action in the same order.
5. Implement append-only decisions and revisions. No endpoint or model input may masquerade as an authenticated owner; #19 must provide the trusted actor boundary before exposure.
6. Implement claim storage and result updates with matching fence. Add explicit evidence record for unknown resolution; storage does not infer provider delivery. Persist state, attempt and audit changes in one transaction.
7. Test two independent DB sessions/processes racing identical keys, edits versus claims and duplicate decisions; synchronize transactions deterministically instead of sleep-based timing.

## Verification and success criteria

Focused unit: `cd apps/backend && uv run --locked pytest -m unit tests/unit/test_states.py` (future file). Integration runs through `make test-integration`, including selected-file filtering introduced in phase 1.

- [x] Enumerated invalid edges fail via persistence and raw SQL using runtime role; no-op duplicate submissions are idempotent, not duplicate approvals/attempts.
- [x] Two claims yield exactly one current claim and one attempt; stale versions/fences cannot change results.
- [x] Edit/rejection preserves history and invalidates executable authorization; kind/destination/attachment mismatch fails.
- [x] Expired claimed send becomes unknown and cannot return to approved/claimed without explicit resolution; restart does not clear it.
- [x] Terminal run retries preserve original logical input and history, increment execution generation and deduplicate concurrent retry submissions; saved completed steps survive fresh connections.
- [x] Multirow failure rolls back decision, action, attempt and audit writes together.

## Risks, security and rollback

Execution evidence (2026-10-22): all 8 workflow tests passed on disposable PostgreSQL. They cover the rejected-edge matrix, synchronized claim/edit/decision/retry races, immutable A/B/A history, exact snapshot mismatch rejection, fencing, expiry/unknown safety, durable completed steps and atomic rollback.

No provider calls, auth acceptance or exactly-once external delivery claim. Trigger changes require backup before migration. Avoid deadlocks through fixed lock order; surface bounded lock conflicts without automatic mutation replay. On a failed invariant, stop and retain sanitized evidence; restore to a fresh isolated target rather than dropping history. Next: phase 3.

<!-- Updated: Validation Session 1 - terminal runs remain immutable; safe failed_known retries may reuse exact-revision approval under #20. -->

<!-- Updated: Red-team Session 1 - align retry generation/idempotency and real local runtime-role checks with phase 1. -->
