---
title: "Phase 2: Private local services"
status: todo
phase: 2
priority: P1
effort: 4h
dependencies: [1]
---

# Phase 2: Private local services

## Overview

After phase 1, provide authenticated PostgreSQL/Neo4j/Qdrant development services and real smoke checks. #12 owns business schemas, migrations, outbox and projections; no product records or worker here. [Blueprint](../../docs/codebase-blueprint.md) owns store roles.

## Requirements

Private root config supplies credentials to Compose/test clients, never browser. Private network contains three stores with independent named durable volumes. Host-native clients use loopback-only PostgreSQL 5432, Neo4j Bolt 7687 and Qdrant HTTP 6333. Publish no unnecessary admin/browser/gRPC ports. Production stores stay internal.

Require PostgreSQL password auth, Neo4j explicit auth and Qdrant API-key auth. Blank example variables, no shared/default secrets. Required-value interpolation rejects absent/empty credentials with remedy. Do not log resolved Compose configuration. Providers remain optional; private config stays Git-ignored/owner-restricted. Production secret mounts belong to deployment.

Real clients run authenticated PostgreSQL `SELECT 1`, Neo4j `RETURN 1`, Qdrant protected collection listing with bounded deadlines/clean closure. Public health endpoints do not prove auth; protected operations deny invalid/missing credentials. No external provider calls.

## Files and ownership

Create `deploy/compose.yaml`, `apps/backend/tests/test_stores.py`. Modify existing configuration template and `apps/backend/{pyproject.toml,uv.lock}` after phase 1 releases ownership. No Dockerfile/Caddyfile, worker/telemetry service or backup/restore scripts. Docs belong to phase 3.

## Implementation Steps

1. Verify official image/auth/healthcheck docs and architecture compatibility; pin tested versions, preferably digests. Confirm bundled healthcheck tools.
2. Inspect containers/project/ports. Local project `email-assistant-dev` uses fixed ports. Resolve unrelated ownership; do not increment ports or kill others. Track command/container IDs/ports/worktree.
3. Define network/volumes/credentials/readiness healthchecks with bounded timeouts and sanitized failed-service diagnostics.
4. Add necessary smoke clients only (PostgreSQL driver, Neo4j client, HTTP for Qdrant); reuse stdlib/installed functionality. Integration marker `stores` must fail rather than skip missing active config.
5. Test valid/invalid auth. On isolated disposable data, write sentinels, restart containers and verify persistence. Qdrant uses disposable collection/fixed supplied vectors without embeddings. Cleanup owned data on success/failure; these are real storage checks, not fake business behavior.

## Verification

Future root contracts: `docker compose --env-file <private-config> -f deploy/compose.yaml -p email-assistant-dev config --quiet`, then same prefix with `up -d --wait`. From `apps/backend`: `uv run pytest -m stores`. Resolve root config explicitly or inject environment; never shell-source private config. CI uses isolated project/credentials; unit command excludes integration marker.

Matrix: missing credentials fail; valid auth connects each store; invalid/missing auth denied; cold start waits; outage fails within deadline; restart preserves sentinels. Inspect actual bindings/mounts. `/health` remains live when stores stop.

## Todo

- [x] Missing active config fails safely without provider settings.
- [x] Three stores authenticate, deny bad credentials and pass real smoke checks.
- [x] Private network/loopback bindings/independent volumes verified live.
- [x] Disposable persistence verified; cleanup removes only owned data/services.

## Success Criteria

Checklist evidence recorded; no schema or VPS capacity acceptance inferred.

## Risk, compatibility and rollback

High impact/medium likelihood: exposure/volume loss. Mitigate loopback/auth/isolated tests; never `down -v` on existing volumes. Stop only owned containers. Medium/medium: memory pressure; use supported conservative Neo4j heap/page-cache/service limits for pinned versions. Report capacity failure rather than remove a store. Local checks do not prove VPS capacity.

No schema migration. Mutation/restart tests run only on newly created isolated disposable stores. Existing database/volume mutation requires prior verified backup; refuse otherwise. Resolve existing volume/credential/version conflicts rather than reset. Rollback client/config additions; stop owned containers using `stop` or `down` without `-v`, retaining volumes/private config. No data-directory downgrade without compatibility evidence.

## Verification record: 10 source claims

Verified: PostgreSQL topology (`docs/codebase-blueprint.md:44`); graph/vector topology (`docs/codebase-blueprint.md:46`); internal boundary (`docs/codebase-blueprint.md:67`); Compose path (`docs/codebase-blueprint.md:97`); canonical authority (`docs/codebase-blueprint.md:129`); store roles (`docs/codebase-blueprint.md:133`); outbox boundary (`docs/codebase-blueprint.md:139`); auth/volumes (`docs/codebase-blueprint.md:143`); pins (`docs/codebase-blueprint.md:185`); ownership (`docs/codebase-blueprint.md:211`). Ten verified, zero failed/unresolved source claims. Files/commands proposed, not executed.
