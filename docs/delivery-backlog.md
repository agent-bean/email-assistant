# Delivery backlog

Status: Published as 7 outcome issues and 35 sub-issues in [Product Project](../README.md), targeting `v0.1-internal`. The accepted [product brief](product-brief.md) owns scope; GitHub issues own execution acceptance and current status.

The codebase blueprint is the first technical task. Ready means scope, acceptance and dependencies are explicit; `blocked` prevents starting before prerequisites are accepted. The owner selects one execution task at a time.

All work targets `v0.1-internal` without a deadline. Manual delivery precedes automation. No implementation starts in this brainstorm session.

## Establish the codebase and owner-controlled workspace

[Outcome #3](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/3)

An accepted blueprint and secure working application foundation support the seven-agent product.

| Work item | Depends on |
| --- | --- |
| [#10 discovery: Settle codebase blueprint and folder structure](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/10) | Accepted product brief |
| [#11 task: Create the blueprint-approved application skeleton](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/11) | [#10](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/10) |
| [#12 task: Add persistent workflow and company data storage](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/12) | [#11](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/11) |
| [#13 task: Restrict application access to the owner](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/13) | [#11](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/11) |
| [#14 task: Manage owner profile and reply guidance](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/14) | [#12](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/12), [#13](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/13) |

## Turn business email into reviewable reply drafts

[Outcome #4](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/4)

Eligible Gmail threads produce grounded drafts without sending automatically.

| Work item | Depends on |
| --- | --- |
| [#15 task: Connect Gmail and read-only Google Calendar](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/15) | [#12](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/12), [#13](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/13) |
| [#16 task: Ingest Gmail threads without duplicate processing](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/16) | [#15](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/15), [#12](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/12) |
| [#26 task: Classify business email and resolve company identity](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/26) | [#16](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/16), [#17](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/17), [#22](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/22) |
| [#32 task: Draft grounded replies from profile and thread](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/32) | [#26](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/26), [#14](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/14), [#22](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/22), [#27](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/27) |

## Produce sourced company research and reusable knowledge

[Outcome #5](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/5)

Company records, web research and supported attachments feed sourced internal reports and approved knowledge.

| Work item | Depends on |
| --- | --- |
| [#17 task: Manage company profiles and Company Info lookup](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/17) | [#12](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/12), [#13](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/13) |
| [#27 task: Research company websites and recent news](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/27) | [#17](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/17), [#22](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/22), [#23](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/23) |
| [#28 task: Extract supported attachments and scanned content](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/28) | [#16](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/16), [#22](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/22), [#23](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/23) |
| [#18 task: Reuse research history without treating drafts as approved knowledge](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/18) | [#12](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/12), [#17](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/17) |
| [#33 task: Publish approved reports to the internal knowledge base](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/33) | [#18](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/18), [#19](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/19), [#20](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/20), [#29](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/29), [#23](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/23) |

## Review reports and authorize exact external actions

[Outcome #6](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/6)

The owner reviews internal reports separately from outgoing messages and controls every send or publication.

| Work item | Depends on |
| --- | --- |
| [#29 task: Assemble sourced internal reports and Markdown output](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/29) | [#27](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/27), [#28](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/28), [#18](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/18) |
| [#30 task: Export reports to PDF and Word](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/30) | [#29](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/29) |
| [#34 task: Build the report and reply review workspace](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/34) | [#13](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/13), [#29](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/29), [#32](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/32) |
| [#19 task: Enforce version-bound human approval decisions](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/19) | [#12](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/12), [#13](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/13) |
| [#20 task: Persist action attempts and reconcile uncertain outcomes](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/20) | [#12](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/12), [#19](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/19) |
| [#35 task: Send approved replies and forwarded reports through Gmail](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/35) | [#15](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/15), [#19](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/19), [#20](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/20), [#30](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/30), [#34](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/34), [#23](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/23) |

## Prepare meetings and run scheduled workflows

[Outcome #7](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/7)

Manual execution precedes configurable morning and pre-meeting automation.

| Work item | Depends on |
| --- | --- |
| [#21 task: Match upcoming meetings to company context](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/21) | [#15](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/15), [#17](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/17) |
| [#36 task: Orchestrate manual runs across the seven agent roles](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/36) | [#26](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/26), [#29](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/29), [#32](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/32), [#21](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/21), [#19](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/19), [#18](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/18) |
| [#37 task: Schedule morning scans and pre-meeting briefings](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/37) | [#36](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/36), [#24](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/24), [#21](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/21) |

## Enforce tool safety and observe agent execution

[Outcome #8](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/8)

Tool controls, budget limits, retention and telemetry govern real executions.

| Work item | Depends on |
| --- | --- |
| [#22 task: Integrate the OpenAI-compatible model gateway](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/22) | [#11](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/11) |
| [#23 task: Enforce all six Tool Harness stages](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/23) | [#11](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/11), [#12](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/12), [#13](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/13) |
| [#24 task: Enforce configurable model and research budgets](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/24) | [#22](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/22), [#12](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/12), [#23](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/23), [#13](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/13) |
| [#31 task: Defend untrusted content and test tool-boundary attacks](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/31) | [#23](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/23), [#19](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/19), [#27](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/27), [#28](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/28), [#18](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/18) |
| [#38 task: Instrument agent runs, tools, usage and traces](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/38) | [#22](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/22), [#23](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/23), [#36](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/36) |
| [#39 task: Provide protected Grafana dashboards on a separate port](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/39) | [#38](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/38), [#13](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/13) |
| [#25 task: Apply configurable retention and owner deletion](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/25) | [#12](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/12), [#18](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/18), [#13](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/13) |

## Validate and deploy the internal release

[Outcome #9](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/9)

The complete product is evaluated, deployed privately and demonstrated with evidence.

| Work item | Depends on |
| --- | --- |
| [#40 task: Build the six-scenario functional and quality evaluation suite](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/40) | [#36](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/36), [#35](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/35), [#33](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/33), [#30](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/30) |
| [#41 task: Verify approval, recovery, injection and budget invariants](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/41) | [#40](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/40), [#31](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/31), [#24](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/24), [#37](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/37), [#25](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/25), [#39](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/39) |
| [#42 task: Deploy the protected app and Grafana on the existing VPS](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/42) | [#39](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/39), [#25](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/25), [#37](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/37), [#35](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/35), [#33](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/33) |
| [#43 task: Verify the complete workflow with the owner account](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/43) | [#42](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/42), [#41](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/41) |
| [#44 docs: Prepare the ten-minute project demonstration](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/44) | [#43](https://github.com/mr-bean-and-agents-squad/email-assistant/issues/43) |

## Coverage

Slide 1: email, research, approval and automation outcomes. Slides 2-3: all seven roles through blueprint, connectors, research, reports, memory and approval work. Slide 4: tool-harness. Slides 5-6: eval and live-acceptance. Slide 7: injection and safety-eval. Slide 8: telemetry and grafana. Slide 9: deadline explicitly removed by the owner. Slide 10: deploy. Slide 11: presentation. Slide 12: reference source only; no additional feature is inferred.

Technical provider choices belong to the blueprint. Private configuration and actual budget amounts are setup inputs, not secrets to collect in issues.
