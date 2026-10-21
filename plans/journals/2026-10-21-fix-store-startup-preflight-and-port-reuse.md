---
title: Fix store startup preflight and port reuse
date: 2026-10-21
summary: Repaired port reuse and startup validation, including Compose interpolation and sanitized parser errors.
---

# Fix store startup preflight and port reuse

## Diagnosis

Both findings reproduced before production edits on `setup/11-application-skeleton`, HEAD `21d87c3`.

- After closing a real loopback TCP connection, plain `bind` failed with `Address already in use`; `SO_REUSEADDR` allowed binding. A reusable probe still rejected a real wildcard listener.
- Compose `config --quiet` accepted short disposable credentials (exit 0), while `load_store_settings()` rejected the same file (exit 1). The original `make stores-up` reached its intercepted Compose startup command despite the invalid file. Interception prevented starting development services during this command-wiring check.

## Changes and boundaries

`scripts/check-stores.py` now probes with `SO_REUSEADDR` through a small testable helper. `Makefile` runs the existing backend validator before Compose, using `uv --project` so root-relative paths, including spaces, retain their meaning. The configuration module exits with the existing sanitized message on validation failure. README documents the enforced startup checks.

Added `apps/backend/tests/unit/test_store_startup.py`: 11 regression cases cover closed TCP sockets, loopback/wildcard listeners, short/missing credentials, file permissions, sanitized errors, valid minimum lengths, relative paths with spaces and environment precedence. Command-wiring tests intercept Compose only; real store behavior is covered separately.

Existing configuration, provider integration, Compose topology, data volumes and schemas were not changed. Store mutations ran only in fresh disposable projects after the runner's offline backups.

## Verification

- Focused regression file: 11 passed; complete unit scope: 18 passed.
- Ruff, ESLint, mypy, TypeScript, OpenAPI/client drift and production build passed. An initial one-character test line-length failure was corrected before the passing rerun.
- Two consecutive `make test-integration` runs passed, 3 tests each. The second run started immediately after cleanup, without a port-delay workaround. Authentication, outages, liveness and restart persistence passed for PostgreSQL, Neo4j and Qdrant.
- `make test-e2e`: 1 passed against the actual API/Vite proxy.
- `git diff --check` passed; final diff review found no additional issue in the changed scope.

The existing TestClient/httpx deprecation warning remains. Vite connection errors occurred only during deliberate E2E outages.

## Cleanup and remaining boundary

Owned projects `email-assistant-test-eaeed2bc167a` and `email-assistant-test-b4ba19fa379a` and their disposable volumes were removed. No containers or listeners remained on ports 8000, 5173, 5432, 7687 and 6333. The pre-existing `rag-demo_qdrant_data` volume remained. E2E-owned API/Vite processes stopped.

Remote CI remains unobserved and the existing plan stays in progress. No commit, push or GitHub mutation occurred; HEAD remains `21d87c3`. No unresolved fix decision remains.

## Follow-up review and repair

Pending review found a further startup-validation defect: Python-dotenv accepted unbraced dollar references literally, while Compose expanded them. A private disposable configuration passed the original validator (exit 0), but real `docker compose config --format json` resolved credential lengths to 2/8/3. No services started during reproduction. Three new regression cases reproduced the bypass before the production repair.

The Make preflight now passes its Compose command to the configuration CLI. After checking private-file permissions, the CLI captures native Compose JSON and validates the effective service credentials with existing `StoreSettings` thresholds. Compose errors, invalid JSON and validation failures remain sanitized; resolution has a 30-second timeout. The redundant unsanitized `config --quiet` step was removed. Runtime dotenv loading and provider boundaries remain unchanged.

Regression coverage now has 16 cases. Startup-command checks resolve configuration with actual Compose and intercept only service startup. Added coverage rejects shortened interpolated credentials, accepts quoted literal dollars and valid expansion, and prevents malformed dotenv values leaking through Compose diagnostics. The interception helper initially asserted against global Compose flags; that test-helper error was corrected before confirming all three interpolation cases failed with startup reached on the pre-fix code.

Final `make check` passed: 23 unit, 3 integration and 1 E2E tests, Ruff, ESLint, mypy, TypeScript, API contract drift and production build. Initial direct lint/type commands from the repository root missed project configuration context; the established Make targets passed without unrelated edits. The existing TestClient warning and deliberate E2E outage proxy errors remain.

Final pending review covered the complete tracked diff and untracked regression/journal files; no verified in-scope findings remain. Disposable project `email-assistant-test-0c7f7e4a7b1a` and its volumes were removed. No project containers or listeners remained on ports 8000/5173/5432/7687/6333; `rag-demo_qdrant_data` remains. HEAD is still `21d87c3`; no commit, push, GitHub mutation or provider calls occurred. AgentWiki publish skipped.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
