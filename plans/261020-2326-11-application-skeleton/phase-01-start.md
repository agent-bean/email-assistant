---
title: "Phase 1: Application shell and dependency gate"
status: todo
phase: 1
priority: P1
effort: 6h
dependencies: []
---

# Phase 1: Application shell and dependency gate

## Overview

Build real API/web shell after resolving #10 acceptance. Read [blueprint](../../docs/codebase-blueprint.md), [working agreement](../../docs/project-context.md), live #10/#11. PR #45 merged at 2026-10-20T16:13:53Z; #10 remains OPEN/unchecked. Record accepted decisions, coverage and any missing evidence before code. If insufficient, stop dependent code and report exact gap. Never silently close #10. Provider gates assigned downstream do not block skeleton indefinitely and are not claimed passed. Planning makes no GitHub changes; execution may record selected-task evidence and refine #11 within authorization.

## Requirements

Settings load at startup from environment or explicitly resolved root private configuration. Validate only active settings, preserve existing provider keys and allow unused blank providers. Sanitized failures name key/remedy without input values, credential URLs or private stack traces. No provider clients, business state, worker or per-request state in globals.

Browser uses same-origin `/api/health`; Vite proxy strips `/api` to FastAPI `/health`. Pydantic response such as `{status: "ok"}` is liveness, independent of store/provider readiness. Shell shows accessible loading/success/unavailable states. Bind API/Vite to `127.0.0.1`, strict fixed ports 8000/5173; no permissive CORS or browser secrets.

FastAPI exports deterministic OpenAPI and generates TypeScript client/types. If generator emits types only, add minimal typed fetch function. No handwritten duplicate response schema. Generation needs no stores/provider secrets. Existing application callers: zero, tracked app paths only contain `.gitkeep`. New consumers: shell/API tests, browser tests and drift check; enumerate concrete callers as implementation creates them.

## Files and ownership

Repo-relative paths. Modify `.env.example`, `.gitignore`. Create backend `apps/backend/{pyproject.toml,uv.lock,.python-version}`, `apps/backend/src/email_assistant/{__init__.py,config.py}`, `apps/backend/src/email_assistant/api/{__init__.py,main.py}`, `apps/backend/tests/{test_health.py,test_config.py}`, `apps/backend/openapi.json`. Create web `apps/web/{package.json,package-lock.json,index.html,tsconfig.json,tsconfig.node.json,vite.config.ts,eslint.config.js}`, `apps/web/src/{main.tsx,app.tsx,style.css}`, `apps/web/src/api/{client.ts,schema.d.ts}`. Use native pytest discovery and ecosystem-required filenames. Remove only replaced `.gitkeep` files. Phase 2 subsequently owns backend manifest/lock and example config; phase 3 owns npm manifest/lock/ignores. No parallel edits.

## Implementation Steps

1. Resolve acceptance gate before code. Inspect port/process owners; reuse only identified compatible project services. Track command/PID/port/worktree for each started process.
2. Verify current official FastAPI/Pydantic/uv/Vite/React/TypeScript compatibility, then pin Python explicitly (evaluate 3.13, not accidental host 3.15), Node/npm and lockfiles. Add no SQLAlchemy/Alembic before #12 needs them.
3. Add minimal settings, FastAPI entry point and health/config tests. Explicit dotenv source prevents CI reading private owner config accidentally.
4. Add shell/proxy/generated client, schema export/generate/check commands. Install only active dependencies. No secrets in `VITE_*`.
5. Configure Ruff/mypy/pytest and ESLint/tsc; ignore runtime outputs/caches/dependencies while preserving private env exclusion.

## Verification

Future backend commands from `apps/backend`: `uv sync --locked`, `uv run pytest -m "not stores"`, `uv run ruff check .`, `uv run mypy src`, `uv run uvicorn email_assistant.api.main:app --host 127.0.0.1 --port 8000`. Web from `apps/web`: `npm ci`, `npm run lint`, `npm run typecheck`, `npm run build`, `npm run api:generate`, `npm run api:check`, `npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`. Scripts implement these proposed contracts, resolving backend paths consistently; drift check regenerates into temporary output and fails without editing tracked files.

Matrix: exact health status/schema; blank providers starts; invalid active config fails nonzero with sanitized remedy; schema export without stores/providers; lint/type/build. Phase 3 verifies real browser states. Store credentials gate active store tests, not liveness.

## Todo

- [x] Dependency gate evidenced before code.
- [x] Locked installs and health/config/static checks pass.
- [x] Deterministic schema/client generation and drift check pass.
- [x] Loopback shell fetches actual API with accessible states.

## Success Criteria

All checklist items have actual command evidence; no provider or deployment acceptance inferred.

## Risk, compatibility and rollback

High impact/medium likelihood: public unauthenticated app or config leak. Mitigate loopback/proxy/sanitized errors and tests. Medium/medium: unsupported runtime/drift; verified pins/checks prevent this. No executable legacy contracts/data; preserve provider keys and folder ownership. Revert only this phase code/manifests; stop owned processes, preserve private config/other edits. No migration.

## Verification record: 10 source claims

Verified: architecture pending implementation (`docs/codebase-blueprint.md:3`); Python/React (`docs/codebase-blueprint.md:19`); frameworks (`docs/codebase-blueprint.md:20`); API folder (`docs/codebase-blueprint.md:76`); backend tests (`docs/codebase-blueprint.md:89`); web source (`docs/codebase-blueprint.md:94`); generated client (`docs/codebase-blueprint.md:107`); no common build required (`docs/codebase-blueprint.md:109`); config-loader gap (`docs/project-context.md:16`); provider keys (`.env.example:1`). Ten verified, zero failed/unresolved source claims. Proposed files/symbols are new; runtime not tested during planning.
