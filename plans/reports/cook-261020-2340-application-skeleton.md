# Application skeleton execution

## Dependency decision before code

Base: `90b4bfb`, branch `setup/11-application-skeleton`. Live reads: #10 is open with unchecked criteria and no comments; PR #45 is merged, with no reviews and explicit remaining provider/setup acceptance. Merge alone is not acceptance.

Sufficient for bounded #11 implementation: `docs/codebase-blueprint.md:229` records owner acceptance of architecture, diagram, folder ownership, seven role contracts and safety rules. Sections on state/recovery, budgets, storage, security, evaluation and backup define each #10 decision deliverable. Lines 231–238 explicitly assign remaining gateway, research/embedding, OAuth and deployment checks downstream. #11 invokes none of those capabilities. This decision allows skeleton only; it neither completes #10 nor claims provider evidence. Owner selected this exact plan for execution. No unresolved skeleton architecture decision remains.

#10 remains open. No issue or Project mutation performed. Existing private configuration and unrelated Docker volume remain untouched. Ports 8000, 5173, 5432, 7687 and 6333 were free; no containers were running.

## Delivered implementation

FastAPI loads only explicitly selected private config, validates active settings with sanitized errors, and serves store-independent `/health`. React/Vite shell uses a generated OpenAPI type and same-origin typed fetch; loading, success, unavailable and keyboard retry states use real API traffic. API/web bind loopback on fixed ports.

Compose provides authenticated PostgreSQL, Neo4j and Qdrant with digest-pinned images, bounded healthchecks, resource limits and independent volumes. Only necessary client ports bind `127.0.0.1`. Test runner refuses occupied ports, creates fresh isolated projects/private credentials, verifies actual mounts/bindings, backs volumes up offline before mutations, and removes only owned disposable resources afterward. Owner configuration/data were not read or modified.

Requested root Makefile owns install/start/static/contract/build commands and `test-unit`, `test-integration`, `test-e2e`, `test`, `check`. Test directories and pytest markers match scopes. Checks run serially because uv environment and fixed ports are shared. README owns verified setup, private credential generation, commands and safe shutdown instructions.

## Verification

Revision tested: base `90b4bfb` plus current intended working-tree source on `setup/11-application-skeleton`; no commit created. Clean temporary clone overlaid with intended source, excluding owner config and generated runtime outputs.

| Check | Result |
| --- | --- |
| Clean `make install` | Locked backend/npm installs pass |
| Clean `make check` | Ruff, mypy, ESLint, TypeScript, generated contract drift and production build pass |
| `make test-unit` | 7 passed; optional blank providers and sanitized active-config errors covered |
| `make test-integration` | 3 passed; protected auth, outage bounds, API liveness and restart persistence across all stores |
| `make test-e2e` | 1 passed; real proxy/API, delayed real network loading, outage/recovery, keyboard retry, mobile overflow |
| Deliberate contract drift | `make api-check` exits 2; restoration passes without tracked-output mutation |
| Missing store configuration path | `make stores-up` exits 2 with remedy |
| README credential creation | New private file mode 0600, independent nonempty secrets, overwrite refused |
| Public source and local links | Scoped secret-pattern scan and changed documentation link checks pass |

Warnings retained: TestClient/httpx deprecation from locked dependencies; npm ESLint deprecation (audit reported zero vulnerabilities). Expected Vite connection errors occur during deliberate API outages. No failures hidden.

## Latest CI OS and actions

Checked official sources on 2026-10-21. Ubuntu 26.04 is newest GA Ubuntu runner, OS 26.04.1 LTS, published image `20261012.163.1`. Owner subsequently selected `ubuntu-latest` for both jobs so GitHub manages future upgrades. That label currently maps to 24.04; announced migration is November 2026. This updates CI runner selection, not owner machine OS or accepted store major versions.

Latest stable action releases verified through GitHub release APIs and tagged action manifests:

- [actions/checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1)
- [actions/setup-node v7.1.0](https://github.com/actions/setup-node/releases/tag/v7.1.0)
- [astral-sh/setup-uv v10.3.0](https://github.com/astral-sh/setup-uv/releases/tag/v10.3.0)
- [Official Ubuntu runner image](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2604-Readme.md)

Actionlint 1.7.12 initially rejected explicit new GA label because its catalog lags official runner availability. Temporary compatibility config recognized that exact label. Owner-selected `ubuntu-latest` is already recognized, so removed the now-unneeded config. Final `go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.12 .github/workflows/ci.yml` passed without custom config or filtered diagnostics. No remote CI run observed; hosted OS/action/browser runtime remains an explicit acceptance gap.

## Review, deviations and cleanup

Scoped code review covered active-config secrecy, generated contract consumers, actual service bindings/auth, disposable-only mutation/cleanup, browser process ownership, CI permissions and Make scope routing. Cook simplifier reviewed store runner/tests/browser spec; resulting changes passed later clean-checkout checks. No unresolved source defect found in this scope. Remote CI acceptance remains pending.

One TypeScript config suffices for app and tooling; no redundant node config. Test placement follows requested scopes rather than initial flat paths. Docker `internal: true` empirically removed host bindings on tested Docker 29.9.1, so local services use private user-defined bridge with loopback publishing. Local egress limitation documented; production internal networking remains downstream.

Final reconciliation: no running Docker containers; original `rag-demo_qdrant_data` volume remains; ports 8000/5173/5432/7687/6333 free. Test API/Vite processes stopped and temporary checkout removed. Existing IDE/tool-owned MCP processes are outside task ownership and were left intact. Owner authorized local commits after selecting automatic runner upgrades. No push, PR, merge, deployment, issue closure or Project mutation performed.

Implementation committed as `4a32c55` (`feat(skeleton): add runnable application and scoped Make checks`). Final workflow with `ubuntu-latest` passed actionlint 1.7.12; staged whitespace, secret-pattern/private-file and updated-link checks passed. Runtime source matches prior clean-checkout checks; only runner selection and owning documentation changed afterward.
