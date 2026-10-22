# Planning evidence — issue 12

## Scout and brainstorm gate

Baseline: `d43df7fffe8324879096153974e52783bedc01dd`. Issue #12 is real; business schema directories are placeholders. #11 is closed and PR #46 is merged with passing application/integration jobs and clean-start evidence. These replace stale prior-session blocking assumptions.

Outcome, constraints, non-goals and acceptance are recorded in plan.md. The accepted PostgreSQL/SQLAlchemy/Alembic direction is reused. Shared-domain ambiguity is required by #17. #19/#20/#42 retain authenticated approval, dispatch/reconciliation and production recovery ownership.

Options: SQLAlchemy sessions plus database constraints/guards preserve the accepted architecture. Application-only validation fails under concurrent/direct runtime writes; raw SQL-only persistence would abandon the accepted ORM/migration direction. Recommended first option depends on short transactions and a shared maintenance protocol; its first failure condition is a writer bypassing those guards. Better approaches: none — the requested accepted direction has the smallest compatible maintenance cost.

Evaluation posted before drafting: https://github.com/mr-bean-and-agents-squad/email-assistant/issues/12#issuecomment-6309573644

## Validation

### Session 1 — 2026-10-21

Trigger: issue-to-plan mandatory validation, mode prompt. Questions asked: 3. All user answers received explicitly.

1. Account history: retain history with at most one active Gmail application-wide (chosen), or fixed single account requiring migration to switch. User selected: "Giữ lịch sử; tối đa một Gmail active toàn ứng dụng (Recommended)". A partial unique index preserves one active connection without deleting history.
2. Terminal-run retry: create linked new run and keep old run immutable (chosen), or reopen old run with attempt history. User selected: "Tạo run mới, liên kết run cũ; giữ run cũ bất biến (Recommended)". Restart of unfinished work still uses existing completed-step checkpoints.
3. failed_known retry: reuse valid exact-revision approval once #20 proves no external effect (chosen), or always request new approval. User selected: "Dùng lại approval còn hiệu lực cho đúng revision; #20 kiểm tra điều kiện retry (Recommended)". unknown remains ineligible until explicit reconciliation.

Phase propagation: phase 1 account design confirmed; phase 2 retry edge changed from requiring fresh approval to guarded reuse; terminal-run semantics confirmed. No new implementation scope.

Source verification: 40 verified, 0 failed, 0 unverified; see [source ledger](./source-verification.md). Whole-plan consistency sweep follows below.

## Red-team

Three read-only code-reviewer subagents completed security, assumption and failure-mode lenses. Standard verification roles: Fact Checker + Contract Verifier. Seven raw findings deduplicated to five (2 High, 3 Medium). All five have codebase file:line evidence. User explicitly selected "Áp dụng cả 5 sửa (Recommended)"; 5 accepted and applied, 0 rejected. No implementation tests or build were run by reviewers.

| Finding | Severity | Concrete failure and evidence | Proposed change |
|---|---|---|---|
| Retry identity collides with run uniqueness | High | New run for unchanged terminal input violates phase 1 key. `docs/codebase-blueprint.md:149` preserves revisions; `:157` shares manual/scheduled dedup keys. | Separate logical work identity from execution generation; idempotent retry submission plus predecessor link; race tests. |
| Ambient environment redirects disposable writes | High | Runner inherits all but four legacy keys at `scripts/check-stores.py:36-46`; new DB/root selectors can override test file per `apps/backend/tests/unit/test_config.py:48-56`. | Explicitly isolate every DB/runtime/migration/artifact selector, then verify resolved target ownership before backup/migration/insert; hostile-parent-env test. |
| Runtime role only proved inside tests | Medium | Compose config defines administrative bootstrap account at `deploy/compose.yaml:5-7`; config exposes only its password at `apps/backend/src/email_assistant/config.py:43-47`. | Document/provision distinct local runtime/migration credentials; runtime must be non-owner/non-superuser; verify actual role/grants/ownership. |
| Content hash uniqueness rejects legitimate revisions | Medium | Edits require new revision per `docs/codebase-blueprint.md:151`; history retained at `:155`. Equal content across records or A/B/A history remains valid. | Hash indexed/validated, never unique; submission identity deduplicates repeated writes. Add equal-content and A/B/A cases. |
| Maintenance lock ends before migration completes | Medium | Blueprint quiesces writes for matched snapshot at `docs/codebase-blueprint.md:187`; direct independent DB connections exist at `apps/backend/tests/integration/test_stores.py:33-40`. | Hold same exclusion before backup through upgrade success/abort, including child commands; synchronize writer in backup-to-upgrade window. |

No finding reverses user decisions. No evidence-free finding remains. All changes were applied after explicit user response. Phase 1 defines retry execution identity, nonunique hashes and local/test role/destination isolation; phase 2 aligns retry and role operations; phase 3 isolates artifact destinations; phase 4 holds one lock across backup/upgrade/abort and tests hostile environment and writer races.

## Presentation brief

Register: Product.
Scene: Solo maintainer reviews persistence safety on desktop or phone in a light workspace.
Direction: Editorial technical reader because phases and trust boundaries need slow inspection.
Color: Restrained; warm paper #faf7f2, ink #0a0a0a, accent #b8232c.
Type: Georgia display plus system sans body; serif/sans contrast with monospace metadata.
Signature: Canonical transaction boundary and four-step implementation rail.
Dials: variance 3, motion 1, density 6.

HTML and AgentWiki requested. No image generation tool is exposed; decorative sketches omitted. AgentWiki CLI and equivalent MCP are absent; private publishing skipped. No task-management tool is exposed; phase checkboxes remain durable progress.

## Whole-plan consistency sweep

Files reread: plan.md and all four phase files. Decision deltas checked: 8 (3 owner validation decisions, 5 accepted red-team fixes). Old four-field run uniqueness, unique-content-hash interpretation, always-fresh approval requirement, test-only role separation and snapshot-only migration lock were removed or explicitly replaced. Matching requirements, implementation steps, risk notes and success criteria agree. Unresolved contradictions: 0. No runtime verification is claimed by these planning gates.

## Artifact verification

`ak plan validate <plan-directory> --json`: valid true. `python3 reports/check-plan.py`: 29 local links, 4 source-matched complete phase dialogs, offline assets and typed-IR fragment verified. HTML embeds final phase source hashes.

The first render check reported invalid `height="auto"` from installed diagram compiler `scripts/compiler/render-svg.mjs:122`. No skill code changed. Assembly removes that invalid generated SVG attribute; CSS retains responsive height. Generated heading IDs were prefixed to avoid collisions between the index, phase dialogs and no-JavaScript fallback. Explicit closed-details hiding and 44px diagram controls removed mobile warnings. Final installed render-check: 375x812, 768x1024 and 1440x900, 0 errors and 0 warnings.

Actual Chromium interaction checks: all four dialogs open, Escape closes and focus returns at widths 375, 768 and 1440; no page overflow, no page errors and no remote asset requests. Reduced-motion emulation reports zero animated diagram elements. The sole local HTTP request was plan.html after inline favicon was added. Temporary server: PID 739385, port 8765, owned planning worktree; stopped with SIGTERM after verification, browser closed and port confirmed free.

Visual critique from desktop/mobile screenshots: calm, precise, spacious. Scores: brief 2, hierarchy 2, spacing 2, alignment 2, typography 2, color 1, depth 2, states 2, responsiveness 1, slop 2, copy 2, craft 2 = 22/24. Color 1: compiler semantic families extend restrained shell palette. Responsiveness 1: dense map labels need reader presentation mode on phones; phase prose reflows and controls remain usable. Three weakest areas improved: mobile control hit areas, hidden-disclosure layout and diagram rendering validity. No item below 1.

No database mutation, migration, application implementation or application runtime test was performed during this planning run. AgentWiki remains skipped because CLI and equivalent connector are unavailable. No HTML public hosting was requested.
