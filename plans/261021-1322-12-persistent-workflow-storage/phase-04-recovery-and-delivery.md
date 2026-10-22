---
title: "Phase 4: Recovery and delivery evidence"
status: todo
priority: P1
effort: 0.75-1.5d
---

# Phase 4: Recovery and delivery evidence

## Context and outcome

Depends on phases 1-3. Read [README](../../README.md), [existing test runner](../../scripts/check-stores.py), [backup policy](../../docs/codebase-blueprint.md#deployment-and-recovery-route), [CI](../../.github/workflows/ci.yml). Prove #12 persistence and migration safety with disposable data. No production backup claim, R2 setup or email/calendar traffic.

## Local operational contract

Finish the guarded local helper introduced in phase 1 as `scripts/storage-snapshot.py`, with documented subcommands `backup`, `migrate` and `restore`. Exact CLI flags are implementation contracts, not current runnable commands. Private config supplies source/target connection and artifact root. Never put credentials in command arguments or public error output.

- `backup`: refuse unsafe/shared/symlink staging, require app writers quiesced, use `pg_dump` custom format against PostgreSQL 17 with compatible client and copy matching private artifact bytes. Output protected manifest with DB/Alembic revision, hashes and counts; verify dump readable. Use restrictive directory/file modes. Failure must not create a success manifest.
- `migrate`: the only documented local upgrade route; take a fresh verified backup before Alembic changes, then apply one head while retaining the same maintenance exclusion from before backup through upgrade completion or abort; never release it between subprocesses. No automatic API startup migration. Refuse active application writers, incompatible DB revision and incomplete snapshot. Fresh disposable empty databases still get backed up first.
- `restore`: validate snapshot manifest and every required file/hash; refuse live/nonempty destination and path overlaps with source or snapshot. Restore to explicitly isolated owned target with sending/scheduling absent or disabled. Never overwrite source. Verify schema revision, constraints, counts, approval/action revisions and artifact references/hashes. Return nonzero for corrupt/incomplete restore; do not claim success after only `pg_restore`.

Because #12 introduces no application data endpoints or worker, local migration requires stopping other DB writers. Use an explicit maintenance protocol and DB-level exclusion/advisory lock shared by all persistence writes; do not rely solely on an unchecked human assertion of quiescence. All application DB/artifact write operations acquire the shared maintenance lock before writing. A parent connection holds the exclusive maintenance lock through matching DB/file snapshot and, for migrate, through Alembic success or failure handling. Do not release it in the backup-to-upgrade interval or when spawning pg_dump/Alembic. A concurrent write must fail or wait boundedly without creating a mixed snapshot. Future workers must follow this protocol. Secrets use private file/environment and sanitized errors; never shell-source configuration.

The helper covers local migration safety only. Reserve `scripts/backup.sh` and `scripts/restore.sh` for the accepted production restic/R2 interfaces owned by #42. No token decryption/access checks can pass before #13/#15; no actual projection rebuild can pass before projector/retrieval work. Mark those downstream checks pending explicitly.

## Files and ownership

- Create/finish `scripts/storage-snapshot.py`; extend `scripts/check-stores.py` to invoke safe migration/restore helpers and pass isolated artifact config. Explicitly strip/override every introduced runtime/migration/restore DB and artifact environment selector, then verify actual server/container, database, role and root ownership before backup, migrations or fixture writes; test conflicting inherited values. Keep current port checks, three-store offline backup and cleanup ownership.
- Create `apps/backend/tests/integration/test_storage_recovery.py`; extend config/transition tests only when changed helpers need it.
- Modify `Makefile`: documented `storage-backup`, `storage-migrate`, `storage-restore` targets with explicit private config/staging/isolated-target inputs; extend `help`. Existing install/check commands stay valid.
- Modify `README.md`: migration/local snapshot/restore operator route, writer exclusion, failure handling and disposable test command. Modify `docs/codebase-blueprint.md` only for claims that now need a precise implemented-vs-downstream boundary; do not mark production scripts implemented.
- Modify `.github/workflows/ci.yml` only if existing integration job cannot run expanded tests; preserve real stores and fixed ports. Keep generated API files unchanged unless actual schema output unexpectedly changes, then investigate scope.
- Record implementation evidence in this plan and a scoped report under `plans/reports/`; do not publish private dumps, fixture credentials, artifact contents or trace bodies.

## Verification sequence

1. Run narrow unit cases for touched config/state/artifact helpers. Inspect fixed ports before starting the disposable store harness; refuse foreign occupants. Track owned Compose project, containers, volumes and test process.
2. In a fresh random test project, back up before migrations and each test mutation sequence. Upgrade to head; create permitted synthetic accounts, two same-domain companies, contacts, a run with completed/pending steps, artifact bytes, revision/approval, one unknown action and independent outbox delivery states.
3. Take matched logical DB/files snapshot with exclusion held. Record a hash/count/revision manifest privately. Stop/start PostgreSQL container and reconnect from a fresh process; assert all canonical states and exact artifact bytes survive. Keep completed steps and unknown intent unchanged.
4. Restore snapshot into a separately named empty disposable database and separate private artifact root on the owned local test cluster; this is not the source database. Verify revision, record references/counts, all constraints and exact bytes, including cached-vector artifacts if present. No actual embedding generation.
5. Test refusal/failure paths: existing target, source overlap, symlink/traversal, corrupted dump, missing/mismatched artifact, incompatible revision, backup failure, interrupted migration and concurrent writer, including a synchronized attempt between completed dump and Alembic upgrade. Verify distinct runtime role cannot own schema, create roles/databases or run DDL; normal local persistence must not use bootstrap/admin identity. Prove source DB and artifact root remain intact. For a failed test migration, restore pre-upgrade snapshot to a new target; never test rollback by deleting owner data.
6. Run `make lint typecheck api-check build`, `make test-unit`, `make test-integration`, then existing `make test-e2e` where browser/runtime prerequisites are available. `make check` is final gate; do not rerun unchanged checks without reason. CI runs same root contracts. Existing API health and web shell behavior must remain intact.
7. Clean only owned test resources after preserving necessary failure evidence. Stop owned long-running processes. Publish sanitized commands/outcomes and link evidence on #12. Keep issue open until acceptance is evidenced; planning alone never closes it.

## Acceptance matrix

| #12 criterion | Evidence |
|---|---|
| Duplicate identities/conflicting actions rejected | Real PostgreSQL UNIQUE/FK/CHECK/trigger violations plus deterministic concurrent-claim/edit tests in phases 1-2 |
| Restart survives; invalid transitions rejected | Fresh-process/container restart checks, complete invalid-edge matrix and runtime-role raw SQL rejection |
| Backup before migrations; tested restore protects data | Pre-upgrade manifest, matched DB/file snapshot, empty isolated restore comparison and source-preservation/failure tests |
| Blueprint storage refinement | Atomic canonical outbox and independent target checkpoint tests, tombstones, provenance and cached-vector metadata tests |

- [x] Focused suites and full required checks pass without secret leakage or owner-data mutation.
- [x] Restore recovers states, revision relationships and exact artifact bytes; pending/unknown states remain safe.
- [x] Local operational route documented and verified; production R2/decryption/projection rebuild remain explicitly unverified.
- [x] Evidence maps to all #12 acceptance criteria; owner review still owns issue acceptance.

## Risks, rollback and abort

Execution evidence (2026-10-22): final `make check` passed lint, typecheck, API drift, build, 30 unit tests, 32 integration tests and 1 real-browser E2E test. Six recovery tests verified actual container restart/fresh-process reads, named record types, exact DB/file restore, different target timezone, runtime read/write and DDL denial after restore, explicit new-role provisioning and refusal/failure paths. A full earlier gate with conflicting inherited storage/PG/test selectors left a synthetic owner sentinel unchanged. All owned test services/volumes and E2E servers were cleaned up.

Independent review findings were repaired and the follow-up review returned no remaining finding in scope. The local operator route is documented in the README and Make help. The controller checkout retains the sanitized report at `plans/reports/cook-261022-issue-12-persistent-storage.md`; shipping must copy it deliberately if needed on this branch. No commit, push, PR or issue update was performed. Hosted CI, owner acceptance, production recovery, token decryption and actual projection rebuild remain pending.

Backups may contain future private business data: use owner-only local storage, exclude them from Git and clean owned disposable copies only. Abort migration on backup/exclusion failure; retain pre-upgrade snapshot and failure status. Additive changes permit old-process compatibility only if tested; do not promise universal downgrade. For bad migrations stop writers, preserve failed source and restore verified pre-upgrade snapshot into a fresh target, then explicitly switch local configuration after checks. A later forward repair is safer than an untested destructive downgrade. Never reset shared volumes, broaden exposure or skip a selected store to get green tests.

<!-- Updated: Red-team Session 1 - hold one exclusion across backup/upgrade/failure; validate runtime role and inherited-environment isolation on actual resolved destinations. -->
