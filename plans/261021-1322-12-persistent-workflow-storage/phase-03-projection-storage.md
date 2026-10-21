---
title: "Phase 3: Canonical projection and artifact storage"
status: todo
priority: P1
effort: 0.75-1d
---

# Phase 3: Canonical projection and artifact storage

## Context and outcome

Depends on phase 2. Read [graph/vector contract](../../docs/codebase-blueprint.md#graph-and-semantic-retrieval), [phase 1](./phase-01-start.md), [phase 2](./phase-02-transactional-state.md). Deliver durable canonical relationship facts, outbox/checkpoint storage and private artifact I/O. The skeleton has no existing worker despite blueprint language; do not invent one here.

## Requirements and schema additions

- Canonical relationship rows reference company/contact/meeting/report/source identities through stable typed record/revision references, with evidence and confirmation status. Add only minimal source/meeting/report identity metadata needed by these references; no ingestion or report generation.
- Mutation + outbox event commit together. Each event has stable ID, entity ID/type, revision, operation (upsert/delete), schema version, timestamp and canonical reference; do not duplicate private document bodies in event payloads.
- Outbox uniqueness `(entity_type, entity_id, revision, operation)` prevents duplicate logical events. One event can target both stores; store separate delivery rows keyed `(event_id, target)` and target checkpoint/version metadata. One store's success cannot mark another successful. SQL storage permits pending, applied and retry metadata without a running projector.
- Store tombstones and monotonically checked entity revisions so delayed updates cannot resurrect deleted content. Preserve enough canonical provenance to rebuild graph without new model inference. Use per-entity revision safety; a single global high-water mark must not skip out-of-order unprocessed events.
- Embedding metadata links chunk/source revision, provider/model/version, dimension, vector artifact hash/key and index-generation identity. Dimension positive; generation/model/dimension must match on reference. Generated vectors belong to private backed-up files. No model/provider default, embedding request or Qdrant collection creation in this issue.
- Artifact classes distinguish retained approved reports from 30-day temporary downloads/intermediates. Store retention metadata only; #25 owns cleanup/deletion execution. Persist deletion markers without cascading away immutable action/approval history.

## Architecture and artifact boundary

Store artifact bytes under a configured private root with generated opaque relative keys. Validate root ownership/permissions, reject absolute/traversal/symlink escapes and non-regular files. Never accept arbitrary client paths. Atomic exclusive writes, checksum verification and an explicit pending/ready state handle the DB/filesystem transaction gap. Publish ready metadata only after durable file write; on rollback/crash, unreferenced files remain identifiable for guarded cleanup. No broad automatic deletion.

Duplicate content hashes need not imply one shared physical file: preserve per-artifact retention/deletion ownership. This avoids premature shared-reference garbage collection. Use stdlib file, hashing and path utilities; no object-store abstraction. Parameterized SQL and versioned payload validation remain mandatory.

## Files and ownership

- Extend `apps/backend/src/email_assistant/models/records.py`; add ordered migration `*_add_projection_storage.py` after phase 2 history.
- Create `apps/backend/src/email_assistant/persistence/projections.py`: canonical event writes and per-target bookkeeping/CAS only.
- Create `apps/backend/src/email_assistant/persistence/artifacts.py`: minimum private-root operations and metadata agreement.
- Create `apps/backend/tests/integration/test_projection_storage.py`, `test_artifact_storage.py`; narrow filesystem rejection tests may share `tests/unit/test_artifacts.py`.
- Extend disposable harness with an explicitly overridden private artifact root and every new DB/index/artifact selector isolated from inherited environment; validate resolved root ownership and DB identity before any I/O. Never discover the owner path. No changes to Neo4j/Qdrant images, public ports or graph/vector clients.

## Implementation steps

1. Write constraints for relationship/provenance, outbox, delivery/checkpoint, index-generation and cached-vector metadata. Apply backed-up migration to disposable DB.
2. Integrate event creation into canonical mutations at one transaction boundary; test rollback with both present or both absent.
3. Implement target-specific applied revision/fence updates. Preserve delete tombstones and reject stale acknowledgments. No cross-store transaction or falsely successful projector execution.
4. Implement opaque-key artifact writes and ready/pending recovery detection. Hash exact bytes and bind ready artifact hashes to action revisions. Use bounded streaming rather than reading unbounded files into memory; attachment content limit remains 20 MB where applicable.
5. Exercise matching metadata and byte checks after fresh DB/file handles. Add embedding metadata without generating fake model output; permitted deterministic test vectors only test storage, never retrieval quality.

## Verification and success criteria

Use real PostgreSQL through `make test-integration`; keep original real Neo4j/Qdrant authentication/restart tests intact. Provider keys remain blank.

- [ ] Canonical mutation failure yields no outbox event; successful mutation yields one event, even for repeated submissions.
- [ ] Neo4j and Qdrant delivery rows remain independent; out-of-order/stale updates and stale delete acknowledgments cannot advance current state incorrectly.
- [ ] Deletion/revision/index-generation references survive restart and are enough for downstream rebuild contracts; this does not prove an actual rebuild.
- [ ] Absolute, traversal and symlink paths are refused; altered/truncated artifact bytes fail checksum verification.
- [ ] Crash before/after file write leaves detectable pending metadata or unreferenced opaque file; never a ready reference to missing bytes.
- [ ] Approved-retained artifacts and temporary artifacts remain distinct; approval/action history is preserved.

## Risks, security and rollback

Filesystem and PostgreSQL are not one transaction. Test each crash point and keep readiness explicit. Do not pretend projection metadata tests prove actual Neo4j/Qdrant writes, semantic retrieval or cross-store deletion; #17/#18/#21/#25/#33 and #40-42 own those integrations. Back up before migrations and abort on incompatible history. Next: phase 4 verifies matched snapshot/restore.

<!-- Updated: Red-team Session 1 - environment isolation includes resolved artifact and database destinations. -->
