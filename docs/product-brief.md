# Email Assistant product brief

Status: Accepted by the owner on October 20, 2026. The codebase blueprint is the
first technical issue; implementation follows its accepted decisions.

## Outcome

Build an assistant for the owner's real business email and meeting preparation.
It researches companies, prepares internal briefings and drafts replies for human
review. The session deliverable is an accepted brief and bounded GitHub parent
issues and sub-issues with verifiable acceptance criteria and explicit dependencies.

## Confirmed constraints

- Support one Gmail account and its Google Calendar.
- Provide a dedicated web application for reviewing and approving work.
- Build the company database and knowledge base within the application.
- Prioritize drafting replies to the sender; the owner approves before sending.
- Process business email from customers and partners; exclude newsletters,
  advertisements and automated messages. A new company has no existing profile
  in the application. Uncertain company identification goes to owner review.
- Draft replies using both the owner's in-app profile and the email thread.
- Produce internal reports with source references and Markdown, PDF and Word
  exports. Keep the outgoing reply separate from the internal report.
- Approve reply sending, report forwarding and knowledge-base publication as
  separate actions.
- Read PDF, DOCX, PNG and JPEG attachments, including OCR for scans, with a
  20 MB per-file limit. Report unsupported, oversized or unreadable attachments
  explicitly; never execute attachment content.
- Deploy on the owner's existing VPS using their domain and Cloudflare account.
- Integrate the owner's existing OpenAI-compatible LLM API gateway.
- Calendar access is read-only; creating or changing events is outside scope.
- When facts are missing, draft clarification questions and flag missing input;
  do not invent prices, deadlines or terms.
- Keep profiles, approved reports and approval history until owner deletion.
  Retain downloaded files and intermediate data for 30 days, and operational
  logs for 30 days. Make retention configurable in Settings. Logs must exclude
  email contents and tokens. App deletion must not delete Gmail or Calendar data.
- Require configured LLM/research budgets before enabling automation. Missing
  usage or price information must appear as unmeasured, never as zero cost.
- Preserve all functional requirements from the source presentation.
- Prioritize real use; the presentation's October 26, 2026 demo deadline does not
  apply to this project. There is no committed delivery date.
- Follow the [working agreement](project-context.md), including the public-data
  boundary, owner-selected execution and blueprint as the first technical task
  after acceptance of this brief.

## Required capabilities from the presentation

- Morning email processing and research for newly encountered companies.
- Calendar-driven preparation before upcoming meetings.
- Seven agent roles: Email, Web Research, Company Info, Calendar, Report
  Generation, Memory and Human Approval.
- Website and recent-news research, company-database lookup, contact information,
  attachment analysis, reusable research history and meeting preparation notes.
- Reports, email composition and sending, forwarding and knowledge-base storage.
- Tool execution checks: schema validation, authentication, scopes, rate limit,
  audit log and execution.
- Prompt-injection defenses across untrusted input and tool boundaries.
- Agent evaluation covering the six presentation scenarios and report quality.
- Grafana on a separate port, agent inventory, request/tool successes and failures,
  cost and latency per request, and request traces with spans.
- Reachable demo deployment and a ten-minute presentation covering the problem,
  solution, architecture, difficulties, resolutions and future direction.

The presentation lists 98% completeness, 42 seconds and 12 references as sample
results. They are not accepted performance or quality thresholds.

## Non-goals for this session

Application implementation, production deployment and sending real email are
outside this brainstorm and backlog preparation session. No feature from the
presentation is dropped without an explicit scope decision.

## Accepted behavior

- Approval binds to the exact content and destination.
- Editing approved content requires approval again; retries must not duplicate
  external actions.
- Deliver manual Run now first, then scheduled email processing at 08:00
  Asia/Bangkok and preparation 24 hours before meetings. Both remain in scope;
  timing is configurable. The owner accepted manual-first delivery followed by
  automation. Newly discovered meetings inside the preparation window
  are handled at the next calendar check.

## Architecture decision and trade-offs

| Approach | Main assumption | First failure condition |
| --- | --- | --- |
| One application with explicit orchestration and seven agent roles | Known email and meeting workflows cover the required outcomes | Evaluation reveals necessary tasks that cannot fit bounded workflows |
| Autonomous delegation between agents | Dynamic delegation materially improves research quality | Unbounded work or unclear approval ownership makes cost and side effects unreliable |
| Independently deployed agent services | Roles need independent scale, deployment or isolation | Operating several services costs more than the single-owner workload warrants |

Accepted: one application with explicit orchestration. Each role has a real
responsibility, input/output contract and observable execution. Seven roles do not
require seven services or seven LLM calls. Human Approval enforces the owner's
decision; a model cannot approve on the owner's behalf.

Better approaches: none — the recommendation preserves the requested multiagent
direction and fits the confirmed single-account workflows. Framework and storage
selection belong to the subsequent blueprint task.

## Integrated acceptance and verification

- Cover all six presentation scenarios with permitted evaluation data and
  explicit expected outcomes, including attachments, calendar matching and KB.
- Research claims have traceable sources; unknown or conflicting facts are
  flagged. An uncertain company match requires owner resolution.
- Replies do not leak internal briefings or invent unsupported commitments.
- Markdown, PDF and Word exports open and preserve content and source references.
- Sending, forwarding and KB publication require approval of the exact action;
  edits invalidate approval and retries do not duplicate effects.
- Injection cases cannot obtain secrets, expand permissions or authorize sends.
- Measure latency, model usage and cost honestly; no sample slide number is
  silently promoted to an acceptance threshold.
- The owner assesses report usefulness and reply tone on the evaluation cases.

## Session acceptance criteria

- The owner accepts product scope and material behavior decisions.
- Each presentation requirement maps to a tracked outcome and bounded work.
- Each sub-issue has scope, non-goals, observable acceptance, verification and
  dependencies; no unresolved product decision is hidden behind Ready status.
- GitHub parent/sub-issue relationships and Project fields are verified live.
- The first technical task remains the project blueprint and folder structure.

## Source

User-supplied `email_assistant.pptx`, slides 1-12, read on October 20, 2026;
the Tool Harness diagram on slide 4 was also inspected. The original lives in
the owner's local course materials and is not published with this brief.
Confirmed decisions come from the owner's brainstorm responses on the same date.

## Implementation discovery and setup inputs

- The blueprint must resolve stack, gateway model capabilities, search/OCR
  providers, storage, deployment topology and backup/restore commands. These are
  explicit discovery deliverables, not assumed implementation facts.
- The owner supplies budget amounts and private deployment/OAuth configuration
  during setup. No secret or real email/calendar content belongs in GitHub.
