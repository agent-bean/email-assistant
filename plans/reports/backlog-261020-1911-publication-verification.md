# Backlog publication verification

Verified on October 20, 2026 (Asia/Bangkok).

The brainstorm deliverable is published: 7 outcome issues and 35 bounded native
sub-issues, all open in milestone `v0.1-internal` and
[Project 12](https://github.com/orgs/mr-bean-and-agents-squad/projects/12).
The [delivery backlog](../../docs/delivery-backlog.md) links all 42 issues and
execution dependencies. [PR #2](https://github.com/mr-bean-and-agents-squad/email-assistant/pull/2)
contains the product brief, backlog and updated repository navigation.

## Verified evidence

- `gh issue list --state all` and all seven parent `/sub_issues` API responses
  match the 42 planned titles and exact 35 parent/child relationships.
- Every child body retains scope, non-goals, acceptance checks, verification and
  explicit prerequisite issue references. The dependency graph is acyclic.
- All 42 Project items have Status `Ready` and Priority `P1`. All 34 dependent
  tasks have `blocked`; [blueprint #10](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/10)
  is the only execution task without prerequisites. Ready expresses refinement,
  not authorization to start. No task was moved to In progress or Done.
- Every issue belongs to `v0.1-internal`. No deadline was imposed.
- Issue sources point to the pushed product brief at commit
  `94acad036a8aa672e14393b3e16417a84b7f66f5`.
- The six evaluation scenario names were checked against source slide 5;
  sample slide 6 quality/performance numbers were not made mandatory thresholds.
- Relative documentation links and `git diff --check` passed. No application
  tests apply because this delivery contains documentation and backlog only.

## Recovery and boundaries

The inherited publication data reused `research` for both a parent and child.
The parent identifier was separated before publication; all 42 unique issue
identities and links were then verified.

One Project update returned `unexpected end of JSON input` after applying its
first ten items. Live state was fetched, the remaining 32 items were updated in
smaller batches, and the complete state was fetched and verified again.

The Project README now points to the published scope instead of describing an
empty management setup. No real email/calendar contents or credentials were
published. No application implementation, deployment or email sending occurred.

## Handoff

PR #2 remains open for review and merge. The next technical task is blueprint
#10, subject to owner selection; stack/provider decisions and private setup
inputs remain explicit deliverables of that task rather than assumptions.
