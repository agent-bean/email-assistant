# Delivery backlog

Status: Prepared from the accepted [product brief](product-brief.md). GitHub issues own execution acceptance and current status.

The codebase blueprint is the first technical task. Ready means scope, acceptance and dependencies are explicit; `blocked` prevents starting before prerequisites are accepted. The owner selects one execution task at a time.

All work targets `v0.1-internal` without a deadline. Manual delivery precedes automation. No implementation starts in this brainstorm session.

## Establish the codebase and owner-controlled workspace

An accepted blueprint and secure working application foundation support the seven-agent product.

| Work item | Depends on |
| --- | --- |
| discovery: Settle codebase blueprint and folder structure | Accepted product brief |
| task: Create the blueprint-approved application skeleton | `blueprint` |
| task: Add persistent workflow and company data storage | `scaffold` |
| task: Restrict application access to the owner | `scaffold` |
| task: Manage owner profile and reply guidance | `persistence`, `owner-auth` |

## Turn business email into reviewable reply drafts

Eligible Gmail threads produce grounded drafts without sending automatically.

| Work item | Depends on |
| --- | --- |
| task: Connect Gmail and read-only Google Calendar | `persistence`, `owner-auth` |
| task: Ingest Gmail threads without duplicate processing | `google-auth`, `persistence` |
| task: Classify business email and resolve company identity | `gmail-ingest`, `companies`, `gateway` |
| task: Draft grounded replies from profile and thread | `triage`, `profile`, `gateway`, `research` |

## Produce sourced company research and reusable knowledge

Company records, web research and supported attachments feed sourced internal reports and approved knowledge.

| Work item | Depends on |
| --- | --- |
| task: Manage company profiles and Company Info lookup | `persistence`, `owner-auth` |
| task: Research company websites and recent news | `companies`, `gateway`, `tool-harness` |
| task: Extract supported attachments and scanned content | `gmail-ingest`, `gateway`, `tool-harness` |
| task: Reuse research history without treating drafts as approved knowledge | `persistence`, `companies` |
| task: Publish approved reports to the internal knowledge base | `memory`, `approvals`, `action-ledger`, `reports`, `tool-harness` |

## Review reports and authorize exact external actions

The owner reviews internal reports separately from outgoing messages and controls every send or publication.

| Work item | Depends on |
| --- | --- |
| task: Assemble sourced internal reports and Markdown output | `research`, `attachments`, `memory` |
| task: Export reports to PDF and Word | `reports` |
| task: Build the report and reply review workspace | `owner-auth`, `reports`, `reply-draft` |
| task: Enforce version-bound human approval decisions | `persistence`, `owner-auth` |
| task: Persist action attempts and reconcile uncertain outcomes | `persistence`, `approvals` |
| task: Send approved replies and forwarded reports through Gmail | `google-auth`, `approvals`, `action-ledger`, `exports`, `review-ui`, `tool-harness` |

## Prepare meetings and run scheduled workflows

Manual execution precedes configurable morning and pre-meeting automation.

| Work item | Depends on |
| --- | --- |
| task: Match upcoming meetings to company context | `google-auth`, `companies` |
| task: Orchestrate manual runs across the seven agent roles | `triage`, `reports`, `reply-draft`, `calendar`, `approvals`, `memory` |
| task: Schedule morning scans and pre-meeting briefings | `manual-run`, `budgets`, `calendar` |

## Enforce tool safety and observe agent execution

Tool controls, budget limits, retention and telemetry govern real executions.

| Work item | Depends on |
| --- | --- |
| task: Integrate the OpenAI-compatible model gateway | `scaffold` |
| task: Enforce all six Tool Harness stages | `scaffold`, `persistence`, `owner-auth` |
| task: Enforce configurable model and research budgets | `gateway`, `persistence`, `tool-harness`, `owner-auth` |
| task: Defend untrusted content and test tool-boundary attacks | `tool-harness`, `approvals`, `research`, `attachments`, `memory` |
| task: Instrument agent runs, tools, usage and traces | `gateway`, `tool-harness`, `manual-run` |
| task: Provide protected Grafana dashboards on a separate port | `telemetry`, `owner-auth` |
| task: Apply configurable retention and owner deletion | `persistence`, `memory`, `owner-auth` |

## Validate and deploy the internal release

The complete product is evaluated, deployed privately and demonstrated with evidence.

| Work item | Depends on |
| --- | --- |
| task: Build the six-scenario functional and quality evaluation suite | `manual-run`, `email-send`, `kb-publish`, `exports` |
| task: Verify approval, recovery, injection and budget invariants | `eval`, `injection`, `budgets`, `schedule`, `retention`, `grafana` |
| task: Deploy the protected app and Grafana on the existing VPS | `grafana`, `retention`, `schedule`, `email-send`, `kb-publish` |
| task: Verify the complete workflow with the owner account | `deploy`, `safety-eval` |
| docs: Prepare the ten-minute project demonstration | `live-acceptance` |

## Coverage

Slide 1: email, research, approval and automation outcomes. Slides 2-3: all seven roles through blueprint, connectors, research, reports, memory and approval work. Slide 4: tool-harness. Slides 5-6: eval and live-acceptance. Slide 7: injection and safety-eval. Slide 8: telemetry and grafana. Slide 9: deadline explicitly removed by the owner. Slide 10: deploy. Slide 11: presentation. Slide 12: reference source only; no additional feature is inferred.

Technical provider choices belong to the blueprint. Private configuration and actual budget amounts are setup inputs, not secrets to collect in issues.
