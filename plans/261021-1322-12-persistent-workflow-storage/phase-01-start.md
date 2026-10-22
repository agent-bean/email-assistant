---
title: "Phase 1: Schema and migration foundation"
status: todo
priority: P1
effort: 1.5-2d
---

# Phase 1: Schema and migration foundation

## Context and outcome

Read [plan](./plan.md), [blueprint](../../docs/codebase-blueprint.md#state-ownership-and-recovery), [config](../../apps/backend/src/email_assistant/config.py), [manifest](../../apps/backend/pyproject.toml), [store runner](../../scripts/check-stores.py) and [Compose](../../deploy/compose.yaml). Current migrations/models/persistence directories contain placeholders; there is no existing business schema to port. The existing integration test creates a disposable `skeleton_probe`; do not confuse it with product data.

Deliver one ordered Alembic migration history and real PostgreSQL schema. No HTTP CRUD or provider integration.

## Requirements and concrete schema

Use UUID primary keys, `timestamptz`, explicit non-null fields and named constraints. JSONB holds versioned payloads, not identities/FKs/current states. Store UTC instants; timezone scheduling belongs to #37. Preserve original display values separately from comparison keys.

| Table group | Required contract |
|---|---|
| accounts | Immutable provider subject keyed by `(provider, subject)`; owner association, active/disconnected state. One active Gmail account via partial unique index; inactive account history retained. No email-as-subject, access token, plaintext refresh token or automatic seed owner. |
| companies, contacts, company_contacts | Stable company IDs; contact identity scoped to account and exact validated address comparison key. Company/contact membership unique per pair. Domains and names are indexed candidates, never globally unique company IDs. Shared domain must permit distinct companies. |
| company_identifiers, sources | `(company_id, kind, normalized_value)` unique; provenance source reference/time and confirmation status. External source keys are scoped by account/provider/type. Only trusted stable external identifiers may receive a broader uniqueness constraint. Uncertain candidates remain unconfirmed; no auto-merge. |
| runs, run_steps | Account, workflow kind, idempotency/input revision key, state, version, timestamps; `(account_id, workflow_kind, logical_key, input_revision, execution_generation)` unique; original generation is 0. Retry keeps logical input unchanged, links a terminal predecessor and increments generation. A unique predecessor link permits one successor; unique account-scoped retry submission key makes repeated retry requests idempotent. Cross-account/input predecessor links and nonconsecutive generations are rejected by FK/trigger. Concurrent retries return the same successor or a conflict, never two runs. Steps unique by `(run_id, step_key, input_revision)`, with persisted input/output references and state. No worker or scheduling loop. |
| revisions, artifacts | Immutable typed document/action content revisions; unique `(record_id, revision)`; content hash is validated/indexed, never unique globally or per record. Equal content across records and A/B/A revision history are valid; submission keys handle duplicate requests. Artifact metadata includes storage key, checksum, byte length, MIME, role, retention class, source revision and deletion marker. Bytes remain in private root; no public absolute path. |
| actions, action_revisions | Stable logical action key scoped by account and kind; current revision and blueprint action state. Immutable revision binds kind, canonical payload, exact ordered destination representation and attachment IDs/hashes. Cross-account/revision links must be rejected by composite FKs or equivalent database constraints. |
| approvals, action_attempts | Append-only approval/rejection history, actor reference and immutable action revision; one effective decision per revision (submission idempotency). Attempts unique by `(action_id, attempt_number)`, recording claim token/fence, start/finish, result, nullable provider ID and sanitized failure code. |

Create audit history for state changes with IDs, revisions, prior/new state and decision metadata only. Domain services in phase 2 enforce valid relations, while DB constraints prevent invalid references and contradictory current records even under concurrent writers. Keep human-readable content out of operational logs.

Do not add budget, scheduler cursor, profile settings or OAuth encryption implementation for unrelated issues. Future migrations add those concrete records when their owning work is selected. An encrypted-token field is not useful until #15 supplies encryption/key handling; do not create a plaintext placeholder.

## Files and ownership

Paths below are relative to repository root; create only these boundaries, adapting filenames to a smaller coherent layout if inspection supports it.

- Modify `apps/backend/pyproject.toml`, `apps/backend/uv.lock`: SQLAlchemy/Alembic plus runtime psycopg.
- Modify `apps/backend/src/email_assistant/config.py` and `.env.example`: PostgreSQL connection settings, private artifact root; preserve existing `APP_ENV_FILE` opt-in and sanitized errors. PostgreSQL settings must load independently from Neo4j/Qdrant credentials. Define separate private runtime and migration/bootstrap credentials; normal persistence refuses superuser, object-owner, CREATEDB/CREATEROLE and schema-DDL privileges. The local setup route, not only CI, provisions and verifies this separation.
- Create `apps/backend/alembic.ini`, `apps/backend/migrations/env.py`, `apps/backend/migrations/script.py.mako`, `apps/backend/migrations/versions/*_create_canonical_storage.py`.
- Create `apps/backend/src/email_assistant/models/{__init__,records}.py`, `persistence/{__init__,database}.py`: metadata and explicit session/transaction ownership; avoid one class per table file.
- Create `apps/backend/tests/integration/test_schema.py`; extend `scripts/check-stores.py` for pre-mutation logical backup and migration bootstrap, explicit isolation of every newly introduced DB/runtime/migration/artifact environment selector and resolved destination ownership checks; unit config assertions go in existing `tests/unit/test_config.py`.

## Implementation steps

1. Recheck #11 acceptance and baseline diff. Stop for incompatible upstream schema work. Inventory existing named volumes without opening owner data. Use the runner's random disposable project only. Override inherited connection/root selectors with harness-owned values and verify resolved database server/container, database name, role and artifact root before backup, migration or insert. A project-name prefix alone is insufficient. Add a conflicting-parent-environment refusal/isolation check.
2. Before first migration or test insert, make and verify a restricted logical PostgreSQL backup of the fresh disposable target; retain the existing offline pre-mutation backup for all three test volumes. Move a minimal guarded local backup/restore helper into this phase so no migration step precedes its safety prerequisite; phase 4 completes the drill. Stop on backup failure.
3. Add runtime dependencies, independent DB configuration and explicit SQLAlchemy session lifecycle. Use URL builders/private environment, never passwords in Alembic INI, arguments or diagnostics. `/health` and OpenAPI generation must still run without database credentials.
4. Create the canonical tables above in one initial revision; reserve subsequent ordered revisions for phase 3 additions. Add indexes for FK lookups and named uniqueness constraints. No DB creation/migration on API import or startup.
5. Back up before upgrade, then run `alembic upgrade head` against the isolated target. A second upgrade is a no-op. Inspect actual constraints, revision and schema diff. Reject unknown future DB revisions and conflicting heads.
6. Exercise inserts and raw-SQL duplicate, null, cross-account and FK failures. Roll back failing transactions and prove no partial records remain. Reconnect through a new engine/process to prove commit durability.

## Verification and success criteria

Existing commands: `make test-unit`, `make test-integration`, `make lint typecheck api-check`. Add narrow real-database cases to existing marked suite; invoke through its disposable harness, never pytest directly against development stores. Focus first on `test_schema.py` through a runner filter added without weakening whole-suite default.

- [x] Empty schema upgrades to one head; repeat upgrade produces no changes; model metadata matches migration.
- [x] Duplicate provider subjects, root run keys and retry submission/predecessor keys, company identifiers within one company, company/contact pairs and action logical keys fail in PostgreSQL.
- [x] Shared company domain, same display name and distinct account-scoped addresses remain representable.
- [x] A genuine retry of unchanged logical input succeeds as a new generation; concurrent duplicate retries yield one successor. Equal-content records and A/B/A revisions remain valid.
- [x] Invalid FK/cross-account/revision references fail; secret values never appear in exceptions/log assertions.
- [x] Missing/invalid DB config fails only DB commands, while `/health` remains usable.

## Risks, security and abort

Execution evidence (2026-10-22): the focused schema suite passed all 10 tests on disposable PostgreSQL 17. It verifies migration/metadata agreement, repeat upgrade, runtime DDL denial, duplicate identities, one active Gmail connection with retained disconnected history, account boundaries, canonical SQL guards and sanitized parameter errors. The unit suite also verifies independent DB configuration and DB-free health.

Review exact DB role grants in phase 2. The current Compose owner role is administrative; application-only validation cannot defend arbitrary direct superuser writes. Avoid claiming that threat model. No real account data is needed. Stop on schema drift, backup failure, an occupied foreign port or missing disposable ownership. After failed migration, keep backups and report revision; do not delete owner volumes or attempt an unreviewed downgrade. Next: phase 2 after schema checks pass.

<!-- Updated: Red-team Session 1 - isolate actual test destinations; separate runtime credentials; define run execution identity and nonunique content hashes. -->
