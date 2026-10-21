---
title: Application skeleton and scoped Make checks
date: 2026-10-21
summary: Local checks passed; latest CI versions verified; remote run pending.
---

# Application skeleton and scoped Make checks

## Outcome

Delivered FastAPI liveness and config, React shell, generated OpenAPI contract and authenticated PostgreSQL, Neo4j and Qdrant. Root Makefile groups unit, integration and E2E checks. Accepted scope and dependency decision remain in execution report.

## Evidence

Clean temporary checkout passed make install and make check: lint, types, contract drift, production bundle, 7 unit tests, 3 real-store integration tests and 1 real-browser E2E test. Deliberate contract drift and missing store config fail with remedies. Disposable volumes backed up before mutations; owned resources cleaned; existing owner data preserved.

Explicit Ubuntu 26.04 selects newest GA runner while ubuntu-latest still selects 24.04. Official latest actions: checkout v7.0.1, setup-node v7.1.0, setup-uv v10.3.0. Actionlint 1.7.12 passed with exact GA runner label configured because upstream catalog lags. Local Docker bridge retained after internal networking suppressed host bindings empirically.

## Remaining

Remote CI unobserved; plan stays in progress. No commit, push, PR or GitHub mutation. Provider and deployment gates remain downstream. AgentWiki publish skipped.

## Owner follow-up

Owner selected `ubuntu-latest` for GitHub-managed runner upgrades and authorized local commits. Removed temporary actionlint compatibility config; final workflow passes actionlint 1.7.12 without custom config. Implementation committed as `4a32c55`; plan and evidence captured separately. No push performed; remote CI remains pending.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
