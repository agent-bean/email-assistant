---
title: "Persistent workflow and company storage"
description: "Add canonical PostgreSQL storage, guarded transitions and a verified local restore route for issue 12."
status: pending
priority: P1
effort: 4-6d
issue: 12
branch: plan/issue-12-persistent-storage
tags: [backend, database, feature]
blockedBy: []
blocks: []
created: 2026-10-21
---

# Persistent workflow and company storage

## Overview

Outcome: implement [issue #12](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/12) against the accepted [blueprint](../../docs/codebase-blueprint.md). PostgreSQL owns durable identities, workflow state, immutable revisions, approvals/actions and projection bookkeeping. Private files own artifact bytes.

Constraints: one owner and one active Gmail connection; SQLAlchemy/Alembic; preserve private configuration, loopback stores and DB-independent `/health`. Back up before every schema/data mutation. Use disposable data for verification.

Non-goals: owner authentication, provider calls, send/reconciliation execution, scheduler, graph/vector indexing or queries, retention jobs, UI changes and production restic/R2 operations. Those remain with their existing issues. This plan delivers their storage contracts without claiming their acceptance.

Acceptance: named record types survive restart; database constraints prevent duplicate identities and conflicting actions; invalid/stale transitions fail atomically; migration backup and isolated restore recover matching records, revisions and artifact bytes. Evidence is required before closing #12.

## Source and dependency evidence

- Baseline: `d43df7fffe8324879096153974e52783bedc01dd` on `main`, PR [#46](https://github.com/mr-bean-and-agents-squad/email-assistant/pull/46) merged; #11 closed with clean-start and application/integration CI evidence. Recheck before implementation.
- [Working agreement](../../docs/project-context.md), [product brief](../../docs/product-brief.md), [backlog](../../docs/delivery-backlog.md).
- [Prior skeleton evidence](../reports/cook-261020-2340-application-skeleton.md). Runtime persistence contracts below are proposed work, not current functionality.
- #17 explicitly allows distinct companies sharing a domain. #19 owns authenticated approval; #20 owns dispatch/reconciliation; #42 owns production recovery.

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Schema and migration foundation](./phase-01-start.md) | Pending |
| 2 | [Transactional workflow state](./phase-02-transactional-state.md) | Pending; depends on 1 |
| 3 | [Canonical projection and artifact storage](./phase-03-projection-storage.md) | Pending; depends on 2 |
| 4 | [Recovery and delivery evidence](./phase-04-recovery-and-delivery.md) | Pending; depends on 3 |

Execution is sequential: migration history, persistence helpers, Makefile and integration runner have one owner at a time. Root paths in phase inventories are repository-relative so this plan survives worktree relocation.

## Architecture and compatibility

Use synchronous SQLAlchemy 2 sessions with the existing psycopg 3 driver, short explicit transactions and Alembic. No API startup migrations, new HTTP endpoints, generic repository framework, event bus or three-store transaction. Add SQLAlchemy/Alembic and move psycopg into runtime dependencies because the application now uses it; resolve compatible versions and commit `uv.lock`.

Database CHECK/UNIQUE/FK constraints own relational invariants; guarded updates and database transition enforcement own legal state edges. Outbox rows share their canonical transaction. Graph/vector checkpoints are separate; artifact hashes and revisions remain canonical.

## Validation Log

Three questions answered on 2026-10-21: retain account history with one active Gmail; terminal-run retry creates a linked new run; safe failed_known retries may reuse valid exact-revision approval under #20. Source verification passed (40/40); full answers in [planning evidence](./reports/planning-evidence.md).

## Red Team Review

Three independent lenses completed; 7 raw findings deduplicated to 5 (2 High, 3 Medium). User approved all 5 fixes; all applied. See [planning evidence](./reports/planning-evidence.md) and [source verification](./reports/source-verification.md).

## Artifacts and handoff

- [Offline HTML reader](./plan.html): user-facing overview after final gates. Markdown phases remain execution authority.
- AgentWiki: skipped; `agentwiki` is absent and no equivalent AgentWiki MCP tools are exposed. No public fallback.
- Runtime task hydration: durable phase checkboxes; no separate task-management tool is exposed.
- Next: plan audit after branch push. Validation and red-team passed; cooking still requires downstream audit and owner task selection.

## Unresolved questions

None after critical-question validation. Red-team fixes applied and source verification passed. No implementation has started.
