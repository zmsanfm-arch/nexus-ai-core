# Handoff: ICT Mentor → NEXUS AI CORE

## Purpose
ICT Mentor is a domain specialist in the Forex workstream and is hosted/governed by NEXUS. It is not an independent agent platform and must not create a parallel orchestrator or execution system.

## Ownership

### Forex / ICT Mentor owns
- ICT education and source-grounded explanations.
- Source lookup and provenance requirements.
- User-supplied chart analysis and trade review.
- Formalization of personal strategy rules only after explicit user confirmation.
- Specialist prompt, schemas, examples, and evaluation tests.

### NEXUS central core owns
- Runtime/interface, manifest loading, registry, and task routing.
- Authentication, authorization, approvals, governance, and audit.
- Shared market data and any account/position access.
- Independent deterministic risk engine and execution gateway.
- Broker connectivity, MT5, secrets, deployment, and service lifecycle.

## Current specialist contract

Enabled tasks: ict.education, ict.source_lookup, ict.chart_analysis, ict.strategy_formalization, ict.trade_review.

Defined but disabled: ict.position_monitoring, ict.position_management, ict.autonomous_execution. Central routing must reject these tasks in the current release.

Only advisory mode is supported. Specialist permission requests are limited to knowledge.retrieve, user_input.read, and chart_attachment.read. No direct live market, account, position, order, broker credential, or MT5 permissions are granted. execution_result is always null.

Canonical schemas:
- agents/ict_mentor/schemas/input.schema.json
- agents/ict_mentor/schemas/output.schema.json

Examples and tests:
- agents/ict_mentor/examples/contract_examples.json
- agents/ict_mentor/tests/test_contract.py

## Required central integration
1. Define/confirm the central specialist interface and manifest loader.
2. Register ict_mentor with only the five enabled task types and advisory mode.
3. Reject the three disabled task types before invoking the specialist.
4. Validate input/output against the supplied JSON Schemas; reject invalid outputs.
5. Grant only the per-invocation read permissions approved by central authorization.
6. Persist source provenance and audit invocation metadata centrally.
7. Do not expose risk engine or execution gateway tools to this specialist in the current release.

## Non-negotiable invariants
- No parallel orchestrator, task manager, or execution gateway.
- No direct MT5/broker/account connection or credentials in the specialist.
- Analysis and trade review do not authorize trading.
- The specialist cannot change its own permissions, mode, or risk limits.
- Source doctrine, user-confirmed rules, and model inferences remain separate.
- No source attribution or user rule is fabricated.

## Current status
Specification and contract files only. This branch has not been merged into main and does not represent a registered/running agent. No broker or live-trading capability exists.
