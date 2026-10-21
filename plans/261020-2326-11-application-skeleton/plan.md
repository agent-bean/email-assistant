---
title: "Issue 11: Application skeleton"
description: "Start a real API and web shell with private local stores and reproducible checks."
status: in-progress
priority: P1
effort: 14h
issue: 11
branch: setup/11-application-skeleton
tags: [backend, frontend, infra, api]
blockedBy: []
blocks: []
created: 2026-10-20
---

# Issue 11: Application skeleton

## Overview

HOLD SCOPE. Deliver FastAPI/Pydantic liveness, React/Vite/TypeScript shell, generated API client, authenticated local PostgreSQL/Neo4j/Qdrant services, and reproducible install/start/CI checks. Fast route; accepted stack and empty scaffold need no research delegation.

Outcome: clean checkout starts using documented commands; shell fetches real API health; missing active configuration fails safely. Constraints: loopback application access until #13, private authenticated stores, no provider calls or private evidence in Git. Non-goals: business behavior/data, worker placeholder, migrations/outbox/projections (#12), login (#13), deployment, telemetry and backup scripts.

[Issue #11](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/11) depends on [#10](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/10). Blueprint acceptance and merged PR #45 do not alone satisfy unchecked #10 acceptance. Before code, reconcile acceptance evidence and record dependency decision; stop dependent code if insufficient. Provider gates explicitly assigned downstream remain there, without waiting for their implementation or claiming they passed.

## Execution order and dependencies

1. [Application shell and dependency gate](phase-01-start.md), 6h: reconcile #10 before code; establish backend, web and generated contract.
2. [Private local services](phase-02-local-services.md), 4h: depends on phase 1; authenticated stores, durable volumes, real smoke checks.
3. [Delivery checks and clean-start evidence](phase-03-delivery-checks.md), 4h: depends on phases 1–2; CI, browser checks, setup docs and evidence.

Phases execute sequentially; file ownership transfers only after predecessor finishes.

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Application shell and dependency gate](./phase-01-start.md) | Pending |
| 2 | [Private local services](./phase-02-local-services.md) | Pending |
| 3 | [Delivery checks and clean-start evidence](./phase-03-delivery-checks.md) | Pending |

## Success Criteria

- [x] #10 dependency reconciled with evidence before application edits; #11 stays blocked if evidence is insufficient.
- [x] Fresh checkout installs locked dependencies and starts API/web using example variables without provider secrets.
- [x] Real `/health` liveness and accessible shell states pass API/browser checks.
- [x] Three authenticated stores pass connectivity and restart persistence smoke checks without business schemas.
- [ ] CI executes actual lint, type, schema/client drift, build, backend, browser and store checks.
- [x] Public evidence sanitized; owned processes stopped; existing volumes intact.

## Execution evidence

Local implementation and clean-checkout `make check` passed: 7 unit, 3 integration and 1 E2E test, plus lint/type/contract/build. Root Make targets and scope directories supersede proposed commands below. See [execution report](../reports/cook-261020-2340-application-skeleton.md). Phase checklists own progress; initial table/frontmatter labels are not derived status. Remote CI remains unobserved, so plan stays in progress. Owner authorized local commits and selected `ubuntu-latest` for GitHub-managed runner upgrades. No push or GitHub mutation performed.

Follow-up review fixes verified port-reuse, bypassed startup validation and dotenv/Compose interpolation mismatch before repair. Added 16 focused regression cases; final `make check` passed all 23 unit, 3 integration and 1 E2E tests plus lint/type/contract/build. Earlier consecutive store runs also verified immediate port reuse after cleanup. Final pending review included untracked files and found no remaining verified in-scope issue. Existing volumes and provider boundaries were preserved during those fix checks. See the [fix journal](../journals/2026-10-21-fix-store-startup-preflight-and-port-reuse.md). Shipping includes these fixes; remote CI acceptance remains pending. The [ship preflight journal](../journals/2026-10-21-prepare-application-skeleton-for-publication.md) records independent verification and the later pre-test Docker-volume baseline.

## Decisions and validation

Chosen: application plus local stores. Assumption: available host supports three selected stores; first failure is measured resource/startup failure. App-only assumes services can wait; first failure is omitted accepted #11 service ownership ([blueprint](../../docs/codebase-blueprint.md):211). Better approach: none within accepted architecture. Pin supported versions after compatibility checks; do not inherit Python 3.15 accidentally. More than eight files reflect distinct manifests, lockfiles, entry points, generated contract, service config and tests; no common build abstraction.

Commands in phases are future contracts, not runnable claims. Planning inspected source/issues only; no application checks/provider gates passed. Each phase records ten verified source claims. No live task-create surface exists; checklists own progress. Live CLI documents file-owned phase state and never rewrites table; initial stub table completed to match generated files.

Validation: 30 source claims checked, zero failed/unresolved. All four plan files reread; dependency/ownership, liveness/auth, provider boundary, version pins and cleanup decisions swept consistently. CLI validation passed; reindex recognizes three phases; active plan pinned. No unresolved contradictions or interview choices. Local links checked separately before handoff.

## Unresolved questions

No stack/product decisions remain. Dependency reconciliation, local compatibility and ports verified. Remaining acceptance gap: observe actual remote CI after authorized publication.

<!-- slug: 261020-2326-11-application-skeleton -->
