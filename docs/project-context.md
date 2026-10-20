# Project context

## Working agreement

The owner selects each task; agents refine, document, update GitHub and execute only selected work. Keep one execution task in progress. Aggregate outcomes do not count toward this limit.

Use the [README](../README.md) for Project and milestone navigation. Resolve repository identity and the default branch from Git/GitHub when needed.

- Release scope: native GitHub Milestone `v0.1-internal`, with no imposed date.
- Implementation plans: `plans/{date}-{issue}-{slug}/plan.md`.

## Sources of truth

Repository Markdown holds accepted product scope, brainstorm conclusions and durable decisions. Issues hold bounded work, acceptance criteria and evidence links. Project fields hold status and priority. Plans hold implementation steps and execution progress. Link between these sources instead of duplicating their content.

Save broad brainstorm results in Markdown before selecting work. An idea does not require an issue immediately. Create an `outcome` parent issue when the owner commits to tracking that outcome; use sub-issues for independently verifiable work. If more research is needed, use a `discovery` issue whose deliverable is a decision or report. Before planning, link the selected issue to its accepted source document. Do not turn all brainstorming notes into tasks automatically.

The first technical task is the project blueprint and folder structure after the product brief is accepted. This configuration does not choose an application stack or generate product backlog.

## Status and priority

| Status | Meaning |
| --- | --- |
| Backlog | Recorded; may need refinement or prioritization. |
| Ready | Outcome, scope, acceptance and dependencies clear. |
| In progress | Owner-selected planning or implementation. |
| Review | Concrete result awaiting review. |
| Verify | Acceptance still needs evidence in the required environment. |
| Done | Acceptance met and evidence linked. |
| Dropped | Not proceeding; record the reason. |

P0: urgent safety or critical blocker. P1: required for the current milestone. P2: lower priority. Apply `blocked` and explain the dependency on the issue; retain its current status.

## Views and release readiness

- Product outcomes: parent issues labeled `outcome`; inspect sub-issue progress and integrated acceptance.
- Backlog: open work for owner prioritization.
- Delivery: execution work excluding aggregate outcomes and Done/Dropped items.
- Release readiness: issues grouped by Milestone across versions, including completed and closed work. Reuse this view for new milestones; no version-specific filter changes are needed.
- Needs attention: open issues labeled `blocked`.

The first milestone targets an internal end-to-end run with the owner's real email and calendar, with approval before sending. The accepted [product brief](product-brief.md) defines detailed scope and integrated acceptance; the [delivery backlog](delivery-backlog.md) maps it to bounded work. Closed issue counts alone do not establish readiness. Close parent outcomes and the milestone only after integrated acceptance with evidence.

## GitHub behavior

Open repository issues are automatically added to the Project. Sub-issues are automatically added; new Project items start in Backlog. Other status transitions are explicit. Merging a PR does not automatically prove acceptance or close its issue. Use `Closes #N` only when merge satisfies all acceptance; otherwise use `Refs #N`, move to Verify and close after verification.

Changes to the default branch require a PR, resolved review conversations and no force push or branch deletion. Required approvals are zero for the solo-owner workflow. CI checks will be added when the application stack and real checks exist.

## Resume a session

Read this file, the owner-selected issue, linked product decisions and its existing plan. Fetch live issue/Project state before updating it. Record results and evidence on the issue, update Project status, and leave a short handoff when unfinished. Do not select another task without the owner.

## Public data boundary

Repository and Project are public. Never publish real email/calendar contents, OAuth tokens, credentials, private logs or personal data. Public evidence must be redacted; keep sensitive runtime evidence in an access-controlled location.
