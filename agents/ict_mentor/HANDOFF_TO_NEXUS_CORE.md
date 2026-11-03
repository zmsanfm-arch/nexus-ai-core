# Handoff: ICT Mentor → NEXUS AI CORE

## Purpose
This document is the integration handoff between the Forex/ICT Mentor workstream and the NEXUS central multi-agent workstream. ICT Mentor is a specialist agent hosted and governed by NEXUS; it is not a second independent orchestration system.

## Source of truth
- Repository: https://github.com/zmsanfm-arch/nexus-ai-core
- ICT implementation branch: `feature/ict-mentor-agent-foundation`
- Current PR: https://github.com/zmsanfm-arch/nexus-ai-core/pull/1
- ICT specification files: `agents/ict_mentor/`
- Do not merge this specification branch until it has been reconciled with the latest `main`. The branch has diverged from `main` and is behind by one commit as of this handoff.

## Responsibilities by workstream

### Forex / ICT Mentor workstream
Owns:
- ICT teaching and source-grounded explanations.
- Chart analysis and trade review.
- Formalization of the user's ICT-standard strategy and limited customizations.
- Knowledge source metadata, retrieval requirements, citations, and evaluation cases.
- Specialist agent behavior and output contract.

### NEXUS central workstream
Owns:
- Agent runtime/interface and manifest loading.
- Agent registry and task routing.
- Authentication, permissions, approvals, governance, audit trail.
- Shared market-data access and broker connectivity.
- Independent deterministic risk engine and execution gateway.
- Deployment, secrets, monitoring, and service lifecycle.

## Required integration sequence
1. Reconcile this branch against the latest `main`; preserve all central-core changes and resolve contract differences before implementation.
2. Confirm or implement a stable specialist interface: `agent_id`, `version`, `capabilities`, `permissions`, input/output schemas, and `run(context) -> AgentResult`.
3. Register `ict_mentor` through the central registry/manifest loader; do not create a parallel orchestrator.
4. Route these task types to the specialist:
   - `ict.education`
   - `ict.source_lookup`
   - `ict.chart_analysis`
   - `ict.strategy_formalization`
   - `ict.trade_review`
   - `ict.position_monitoring`
   - `ict.position_management`
   - `ict.autonomous_execution`
5. Connect a provider-neutral retrieval interface and source provenance. Each retrieved chunk must retain source title, canonical URL, timestamp/segment, and source type.
6. Keep the agent in `advisory` mode by default. Position management and autonomous execution remain disabled unless separately authorized.
7. All broker actions must pass through the central execution gateway and independent risk engine. The model must never hold broker credentials or call MT5 directly.
8. Add integration tests for routing, authorization, fail-closed behavior, source citations, and audit logging.
9. Start with XAUUSD on MT5 Demo. Do not enable live execution as part of the initial integration.

## Specialist output contract (minimum)
Return a structured result containing:
- `agent_id`, `mode`, `answer`
- `source_claims` (claims with source URL and timestamp/segment)
- `user_rules_used` (only explicitly documented user rules)
- `agent_inferences` (clearly separated from source doctrine)
- `proposed_actions`
- `risk_decision`
- `execution_result` (null unless an authorized gateway action was actually acknowledged)
- `uncertainties`

## Authorization invariants
- Model output is never authorization.
- A chat request to analyze a chart or discuss a position is not permission to trade.
- The specialist cannot grant or expand its own permissions.
- Risk limits and kill switch are enforced outside the model and cannot be overridden.
- Reject stale market data, duplicate actions, invalid broker state, and failed risk checks.
- Never claim an order succeeded without broker acknowledgement and state reconciliation.

## User decisions still required in the Forex workstream
The user will provide chart examples and define their actual entry/exit, invalidation, session, liquidity, MSS, FVG, and risk rules. Do not invent these rules or silently substitute generic ICT interpretations. Preserve a clear distinction between official ICT source doctrine and the user's personal playbook.

## Current implementation status
The ICT files in this branch are a design specification, not a running agent. Runtime registration, retrieval, routing, execution gateway, and broker integration are not yet complete.
