---
title: "Phase 3: Delivery checks and clean-start evidence"
status: todo
phase: 3
priority: P1
effort: 4h
dependencies: [1, 2]
---

# Phase 3: Delivery checks and clean-start evidence

## Overview

After phases 1–2, reproduce clean installation/start and actual local/CI checks. Record sanitized #11 evidence; build alone does not prove acceptance. [Working agreement](../../docs/project-context.md) governs public evidence.

## Requirements

CI installs pinned Python/uv/Node/npm and locked dependencies, runs unit/config, lint/type/build and schema/client drift checks. Integration job starts isolated real stores with disposable credentials, waits, tests auth/connectivity/restart and cleans owned services even on failure. Browser starts actual API/Vite and fetches through proxy. No mocked success API or fake business data.

Exclude private config/resolved Compose config, credential URLs/private traces from logs. Generate/mask disposable CI credentials; no owner secrets. Inspect server ownership before fixed ports 8000/5173. Reuse only compatible identified local servers; CI owns fresh processes. Track command/ID/port/worktree, clean every exit.

## Files and ownership

Create `.github/workflows/ci.yml`, `apps/web/playwright.config.ts`, `apps/web/tests/shell.spec.ts`. Modify `apps/web/{package.json,package-lock.json}`, `.gitignore` for browser/check scripts/outputs. Modify existing `README.md`, `docs/project-context.md` only stale setup/scaffold/check statements. Update only stale config-loader implementation claims in `docs/codebase-blueprint.md`; preserve architecture/gates. README/manifests own commands; link rather than duplicate. Plan `reports/` owns execution evidence.

## Implementation Steps

1. Add Playwright and `npm run test:e2e`; tracked `webServer` commands start API/web with readiness deadlines/graceful cleanup. CI installs Chromium/system dependencies.
2. Test real loading/success through proxy, keyboard access/status and API-unavailable/retry behavior. Stop only owned API for outage; restore afterward. Loading uses delayed real startup if needed, no fake health fixtures.
3. Add least-permission CI jobs, locked installs/timeouts and actual store/browser/schema checks. Unique CI project names prevent overlap; isolated runners use fixed ports. Workflow syntax alone is insufficient.
4. README documents verified versions, root private config/permissions, active keys, installs/ports/start/check/stop, occupancy diagnosis/troubleshooting. Explain liveness/readiness, deferred providers, local scope and safe volumes.
5. Reproduce documented route in isolated temporary checkout without owner config: locked install, missing-active-config remedy, restricted disposable config, startup/health/browser/store restart/all CI-equivalent checks. Record revision/commands/results/cleanup, sanitized. Stop processes before removing checkout.
6. Review public/config contracts/tracked artifacts for leaks; compare evidence with #11 acceptance. Do not close #10 or claim downstream gates passed. GitHub/commit/PR actions follow controller authorization, outside planning.

## Verification

Future backend commands from `apps/backend`: `uv sync --locked`, `uv run ruff check .`, `uv run mypy src`, `uv run pytest -m "not stores"`, `uv run pytest -m stores`. Web from `apps/web`: `npm ci`, `npm run lint`, `npm run typecheck`, `npm run api:check`, `npm run build`, `npm run test:e2e`. README/CI use same directories/config rules. Real failures return nonzero. Temporarily introduce backend contract drift to prove detection, then restore.

| Layer | Evidence |
| --- | --- |
| Unit/config | Health schema; optional providers absent; sanitized invalid config |
| Contract | Deterministic generation; introduced drift rejected |
| Integration | Three stores; invalid auth denial; bounded outage; persistence |
| Browser | Actual proxy/API success; loading/error/retry; keyboard access |
| Clean start | Documented install/config/start/check/stop reproduced |
| CI | Actual remote run; local equivalent reported separately |

## Todo

- [x] Local/browser/store checks pass with evidence.
- [x] Clean checkout reproduces README without provider secrets.
- [ ] CI executes every check; remote result pending until observed.
- [x] Docs/links correct; no private tracked artifacts; owned processes stopped.

Execution: [report](../reports/cook-261020-2340-application-skeleton.md) records clean-checkout `make check`, negative checks and cleanup. Final test locations are backend `tests/unit/`, backend `tests/integration/` and web `tests/e2e/`; markers are `unit` and `integration`. Root Makefile owns executable commands. Remote CI remains pending.

## Success Criteria

Checklist evidence distinguishes local checks, remote CI and issue acceptance.

## Risk, compatibility and rollback

High impact/medium likelihood: leak/destructive cleanup. Use sanitized summaries/disposable credentials/task-owned identities; never `down -v` on existing volumes. Medium/medium: CI misses locally tested contract; use exact README commands/inspect remote results. Medium/medium: startup flakes; strict ports/readiness deadlines, no arbitrary sleeps. Preserve navigation/provider keys. Revert CI/docs/browser independently while retaining phases 1–2/volumes; missing checks leave #11 unaccepted.

## Verification record: 10 source claims

Verified: no application (`README.md:5`); folders (`README.md:9`); plan naming (`docs/project-context.md:10`); evidence (`docs/project-context.md:14`); loader gap (`docs/project-context.md:16`); merge not acceptance (`docs/project-context.md:48`); CI pending (`docs/project-context.md:50`); public boundary (`docs/project-context.md:58`); test ownership (`docs/codebase-blueprint.md:109`); pytest/Playwright (`docs/codebase-blueprint.md:209`). Ten verified, zero failed/unresolved source claims. Existing app consumers zero; new shell/API/store/browser/CI consumers explicitly listed above.
