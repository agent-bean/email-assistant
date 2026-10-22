# Email Assistant

[Product Project](https://github.com/orgs/mr-bean-and-agents-squad/projects/12) | [Milestones](https://github.com/mr-bean-and-agents-squad/email-assistant/milestones) | [Working agreement](docs/project-context.md)

The [product brief](docs/product-brief.md), [blueprint](docs/codebase-blueprint.md) and [backlog](docs/delivery-backlog.md) define scope and ownership. Local development runs FastAPI liveness, a React shell and authenticated PostgreSQL, Neo4j and Qdrant. Backend storage provides canonical records, guarded workflow transitions, immutable approvals, projection bookkeeping and private artifacts. HTTP business endpoints, login, provider execution, projectors and deployment remain downstream.

## Install and run

Use Python 3.13 (tested 3.13.16), uv 0.13.3, Node 24.22.0, npm 12.2.0, GNU Make, Docker Engine with Compose v2 and Chromium. Application directories own runtime pins and dependency lockfiles. Compose pins tested images by digest. This is a local development route.

Check fixed ports with `ss -ltnp` or `lsof -i :8000`: API/web use 8000/5173; stores use 5432/7687/6333. Identify occupants before starting. Stop only your own compatible old service; do not change ports or stop unrelated processes.

From the repository root:

```sh
make install
```

In separate terminals:

```sh
make api
```

```sh
make web
```

Open http://127.0.0.1:5173. Vite proxies `/api/health` to `/health`, which returns `{"status":"ok"}` even during store outages. This is process liveness, not readiness. Shell states cover loading, connected and unavailable, with keyboard-accessible retry. No stores/provider keys are needed for API/web. Stop servers with Ctrl+C. Both bind loopback; owner login is downstream, so do not expose them publicly.

## Private local stores

Preserve existing owner configuration. Create a new Git-ignored private file from the example, refusing overwrite. This generates independent credentials without printing them:

```sh
python3 - <<'PY'
from pathlib import Path
import os
import secrets

path = Path('.env.local')
content = Path('.env.example').read_text()
for key in ('POSTGRES_PASSWORD', 'NEO4J_PASSWORD', 'QDRANT_API_KEY'):
    content = content.replace(key + '=\n', key + '=' + secrets.token_hex(24) + '\n')
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as stream:
    stream.write(content)
PY
```

Provider keys stay optional/blank. Active store keys: `POSTGRES_PASSWORD`, `NEO4J_PASSWORD` (16+ characters) and `QDRANT_API_KEY` (32+). Use generated independent secrets without whitespace. `APP_ENVIRONMENT` defaults to `local`; other values fail with a sanitized remedy. Backend private files require owner-only permissions (for example `chmod 600`) and are opt-in through `APP_ENV_FILE`; environment variables override file values. No automatic dotenv discovery or shell-sourcing. Never put secrets in `VITE_*`, Git, logs, shell arguments or browser code.

From the repository root:

```sh
make stores-up ENV_FILE=.env.local
```

`make stores-up` checks owner-only file permissions and validates credential lengths against Compose's resolved service values before startup. Missing or short credentials and invalid Compose configuration fail with sanitized errors; Compose interpolation and environment precedence apply. Do not print resolved Compose config. Local stores share a private user-defined bridge and publish only required ports to `127.0.0.1`. Docker `internal: true` suppressed published ports on the tested engine; host-native clients need this bridge route. No admin/browser/gRPC ports publish. This local network allows egress; deployment owns production internal networking and secret mounts. Bounded Compose healthchecks establish startup, while protected client operations verify authentication separately.

Stop stores without deleting their independent named data volumes:

```sh
make stores-down ENV_FILE=.env.local
```

Never use `down --volumes` for existing development data. Password changes do not reinitialize existing databases. Do not reset volumes/downgrade versions to fix auth. Inspect service status and private logs without sharing secrets; back up before data/schema changes. Report memory/startup failures rather than removing a selected store. Local checks do not establish VPS capacity.

## Canonical storage and local recovery

PostgreSQL 17 owns canonical state; private files hold artifact bytes. SQLAlchemy metadata lives in [records.py](apps/backend/src/email_assistant/models/records.py), with ordered frozen DDL in [Alembic migrations](apps/backend/migrations/versions/). API startup and `/health` never connect to or migrate storage. Persistence functions require explicit short transactions through [transaction()](apps/backend/src/email_assistant/persistence/database.py). Future workers must use the same maintenance protocol.

Install PostgreSQL 17 client tools and put that version's binaries first on `PATH`; both `pg_dump --version` and `pg_restore --version` must report 17.x. Stop other application writers before maintenance. Create separate absolute, owner-only directories for artifacts and snapshots (`0700`, no symlink ancestors). Each operation requires a new snapshot directory under that private parent; never reuse staging or place it inside the artifact root.

Set `STORAGE_*` values from [.env.example](.env.example) in a private maintenance file. The configured database must already exist. For the local Compose cluster, the admin identity is `email_assistant` and its password is the existing effective PostgreSQL credential. Use an independent generated runtime password and a distinct runtime role. Do not copy admin credentials into ordinary runtime configuration: runtime needs only the database, runtime credentials and artifact root; omit both admin keys there. Graph/vector/provider credentials are unnecessary for storage commands.

For the first schema upgrade, provision a new runtime role explicitly:

```sh
make storage-migrate ENV_FILE=/absolute/private/storage.conf \
  STAGING=/absolute/private/snapshots/before-first-upgrade PROVISION_RUNTIME=1
```

Provisioning refuses an existing role instead of replacing its password or assuming ownership. On later upgrades omit `PROVISION_RUNTIME=1`; the helper refreshes DML grants and verifies the existing runtime login. Runtime cannot own application tables, create schemas/tables/temporary tables/roles/databases, delete history or mutate migration metadata. Admin credentials are used only for maintenance.

The [snapshot helper](scripts/storage-snapshot.py) is the local operator route. Every migration takes a fresh, verified database dump plus matching artifact copies and a private hash/count/schema/constraint manifest before applying Alembic. One exclusive database advisory lock stays held through backup and upgrade, including subprocesses and failures. Persistence writes and database triggers share that lock, so concurrent writers fail or wait boundedly. No worker timer, sending or scheduling starts here.

Create an additional matched backup without upgrading:

```sh
make storage-backup ENV_FILE=/absolute/private/storage.conf \
  STAGING=/absolute/private/snapshots/manual-backup
```

For restore, create a separately named, empty owned database through a private admin client and a new empty private artifact root. Put those target selectors in a separate owner-only configuration file. Keep sending and scheduling absent or disabled. Restore never overwrites the source, and refuses active target sessions, nonempty targets, source/path overlap, symlinks and corrupt or incomplete snapshots:

```sh
make storage-restore ENV_FILE=/absolute/private/restore.conf \
  SNAPSHOT=/absolute/private/snapshots/manual-backup
```

Restore first backs up the empty target into a new `restore-preimage-*` directory beside the source snapshot. It then verifies restored records, revisions, constraints and artifact bytes, reapplies runtime grants and verifies runtime access. On a separate cluster without that runtime role, add `PROVISION_RUNTIME=1` with new private runtime credentials; role passwords are not part of the dump. Database fingerprints normalize timestamps to UTC, independently of target timezone.

Any failure returns nonzero. Preserve the source, pre-upgrade backup and failed staging/target for private inspection; a failed restore may leave a partial isolated target. Stop its users, create another empty target and restore a verified snapshot before explicitly switching configuration. Do not reset shared volumes, retry against a nonempty target or run destructive downgrades. Dumps and manifests may contain private data; keep them outside Git and owner-only. This local drill does not verify production restic/R2 backup, decryption, graph/vector rebuild or disaster recovery.

## Checks and test scopes

The [Makefile](Makefile) owns root commands. Run `make help` for the list. CI uses these same targets.

| Scope | Location | Command | External services |
| --- | --- | --- | --- |
| Unit | `apps/backend/tests/unit/` | `make test-unit` | None; isolated config and in-process health |
| Integration | `apps/backend/tests/integration/` | `make test-integration` | Disposable real PostgreSQL, Neo4j and Qdrant |
| E2E | `apps/web/tests/e2e/` | `make test-e2e` | Chromium, actual API and Vite |

Backend tests also support pytest markers `unit` and `integration`; unknown markers fail. `make test` runs all scopes; `make check` runs lint, typecheck, API drift, build and every test scope. Checks run serially because uv shares one environment and integration/E2E own fixed ports.

```sh
make lint typecheck api-check build
make test-unit
make test-integration
(cd apps/web && npm exec -- playwright install chromium)
make test-e2e
# Full verification after browser installation:
make check
```

For clean Linux CI, install browser system libraries using `npm exec -- playwright install --with-deps chromium` from `apps/web`. E2E tests require ports 8000/5173 free, start actual API/Vite, test loading/outage/retry without fake responses, and stop owned processes. Stop manual servers before running them.

After intentional API changes, run `make api-generate`, review both generated files, then run `make api-check`. Drift checking regenerates temporary outputs and fails without changing checked-in artifacts. Schema generation needs no running stores or provider credentials.

Stop development stores before `make test-integration`. The runner creates a random isolated Compose project and restricted disposable config, verifies actual loopback bindings and PostgreSQL system identity, backs up fresh volumes offline, then performs a backed-up schema upgrade before pytest. Each storage test takes a fresh logical/file preimage. Inherited `STORAGE_*`, `PG*` and test selectors are removed. Checks cover authentication, outages, independent API liveness, database invariants/races, private artifact failures, restart and isolated restore. Cleanup removes only owned disposable services/volumes. Occupied ports are refused; direct persistence tests without disposable context fail. Existing owner data and providers are untouched. Focus a storage suite with `python3 scripts/check-stores.py tests/integration/test_schema.py -x`.

[CI](.github/workflows/ci.yml) runs application, contract, browser and real-store checks in separate jobs. Both jobs use `ubuntu-latest`, letting GitHub manage future runner upgrades. Action release pins were checked against official sources on 2026-10-21. Local results do not prove remote CI, merge or deployment. Execution evidence belongs to the selected plan and its linked report.
