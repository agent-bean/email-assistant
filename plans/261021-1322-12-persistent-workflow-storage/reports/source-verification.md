# Source verification

Baseline: `d43df7fffe8324879096153974e52783bedc01dd`. Standard tier: Fact Checker and Contract Verifier; 10 claims per phase. Proposed files/commands are future contracts, not falsely reported as existing.

| Phase | Claim/source token | Evidence | Result |
|---|---|---|---|
| 1 | `requires-python = ">=3.13,<3.14"` | `apps/backend/pyproject.toml:4` | VERIFIED |
| 1 | `psycopg[binary]==3.3.6` | `apps/backend/pyproject.toml:13` | VERIFIED |
| 1 | `def private_source()` | `apps/backend/src/email_assistant/config.py:22` | VERIFIED |
| 1 | `env_prefix="APP_"` | `apps/backend/src/email_assistant/config.py:18` | VERIFIED |
| 1 | `POSTGRES_DB: email_assistant` | `deploy/compose.yaml:6` | VERIFIED |
| 1 | `postgres:17.6` | `deploy/compose.yaml:3` | VERIFIED |
| 1 | `SQLAlchemy/Alembic` | `docs/codebase-blueprint.md:20` | VERIFIED |
| 1 | `migrations/         # Alembic` | `docs/codebase-blueprint.md:88` | VERIFIED |
| 1 | `/health` | `apps/backend/src/email_assistant/api/main.py:23` | VERIFIED |
| 1 | `Consistent offline backup` | `scripts/check-stores.py:116` | VERIFIED |
| 2 | `Run state: queued` | `docs/codebase-blueprint.md:149` | VERIFIED |
| 2 | `Action state: draft` | `docs/codebase-blueprint.md:151` | VERIFIED |
| 2 | `Editing creates a new revision` | `docs/codebase-blueprint.md:151` | VERIFIED |
| 2 | `transactional claims with leases` | `docs/codebase-blueprint.md:153` | VERIFIED |
| 2 | `fencing/version checks` | `docs/codebase-blueprint.md:153` | VERIFIED |
| 2 | `becomes unknown until reconciled` | `docs/codebase-blueprint.md:153` | VERIFIED |
| 2 | `never blindly resend` | `docs/codebase-blueprint.md:153` | VERIFIED |
| 2 | `independent exact-content approvals` | `docs/codebase-blueprint.md:9` | VERIFIED |
| 2 | `test_explicit_private_file_and_environment_precedence` | `apps/backend/tests/unit/test_config.py:48` | VERIFIED |
| 2 | `POSTGRES_USER: email_assistant` | `deploy/compose.yaml:5` | VERIFIED |
| 3 | `canonical mutation and projection outbox event` | `docs/codebase-blueprint.md:139` | VERIFIED |
| 3 | `separate checkpoints` | `docs/codebase-blueprint.md:139` | VERIFIED |
| 3 | `deletion tombstones` | `docs/codebase-blueprint.md:139` | VERIFIED |
| 3 | `embedding model/version, dimensions` | `docs/codebase-blueprint.md:141` | VERIFIED |
| 3 | `private backed-up artifact store` | `docs/codebase-blueprint.md:141` | VERIFIED |
| 3 | `rebuilding Neo4j requires no new LLM inference` | `docs/codebase-blueprint.md:141` | VERIFIED |
| 3 | `never mix incompatible vectors` | `docs/codebase-blueprint.md:141` | VERIFIED |
| 3 | `retained approved-report artifacts` | `docs/codebase-blueprint.md:155` | VERIFIED |
| 3 | `20 MB per-file limit` | `docs/product-brief.md:28` | VERIFIED |
| 3 | `def test_authentication` | `apps/backend/tests/integration/test_stores.py:55` | VERIFIED |
| 4 | `def ports_available` | `scripts/check-stores.py:16` | VERIFIED |
| 4 | `email-assistant-test-` | `scripts/check-stores.py:35` | VERIFIED |
| 4 | `def terminate` | `scripts/check-stores.py:29` | VERIFIED |
| 4 | `"down", "--volumes", "--remove-orphans"` | `scripts/check-stores.py:182` | VERIFIED |
| 4 | `check: lint typecheck api-check build test` | `Makefile:67` | VERIFIED |
| 4 | `test-integration:` | `Makefile:59` | VERIFIED |
| 4 | `make install-backend test-integration` | `.github/workflows/ci.yml:35` | VERIFIED |
| 4 | `restic to Cloudflare R2` | `docs/codebase-blueprint.md:187` | VERIFIED |
| 4 | `Do not back up a live PostgreSQL data directory` | `docs/codebase-blueprint.md:187` | VERIFIED |
| 4 | `Deployment work owns the scripts` | `docs/codebase-blueprint.md:194` | VERIFIED |

## Contract consumers

`private_source()` has two production callers, `load_settings()` and `load_store_settings()`, plus one direct `validate_store_compose()` use, all in config.py; existing config tests cover behavior. New DB settings must be independent, without changing these call contracts. `load_settings()` is used by API startup; `load_store_settings()` by real-store integration tests. Root Make targets are consumed by README and `.github/workflows/ci.yml`; plan names each surface. No HTTP endpoint or generated web contract change is planned. `check-stores.py` owns marked integration execution and cleanup; new settings require explicit environment isolation and actual-target validation before mutation.

## Results

Claims checked: 40. Verified: 40. Failed: 0. Unverified: 0. No runtime implementation tests executed during planning. GitHub issue #17 independently confirms shared-domain companies; #11 closed/PR #46 merged evidence verified live before drafting.
