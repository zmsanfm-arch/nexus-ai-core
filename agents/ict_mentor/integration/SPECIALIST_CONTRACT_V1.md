# ICT Mentor Specialist Contract v1

## Scope
ICT Mentor is a specialist only. NEXUS AI CORE owns orchestration, task lifecycle, authentication, authorization, approvals, audit, market-data services, deterministic risk decisions, and execution. ICT Mentor owns no parallel orchestrator, task manager, scheduler, broker adapter, MT5 connector, or execution gateway.

## Routable capabilities

| Task type | Release status | Purpose |
|---|---|---|
| ict.education | enabled | Explain ICT concepts with source-grounded claims |
| ict.source_lookup | enabled | Find and summarize permitted source segments |
| ict.chart_analysis | enabled | Analyze user-supplied chart/image/data only |
| ict.strategy_formalization | enabled | Formalize rules explicitly supplied or confirmed by user |
| ict.trade_review | enabled | Review trades against supplied evidence and rules |
| ict.position_monitoring | defined, disabled | No live position access |
| ict.position_management | defined, disabled | No position modification |
| ict.autonomous_execution | defined, disabled | No order submission or cancellation |

Disabled task types must be rejected by central routing, not passed to the model as executable tasks.

## Input contract
Canonical schema: schemas/input.schema.json. Every invocation requires task_type, mode (advisory only), and non-empty request. Optional context, user chart/trade data, confirmed user rules, retrieved source segments, and correlation ID may be supplied. NEXUS authenticates and authorizes before invocation.

## Output contract
Canonical schema: schemas/output.schema.json. All nine required fields are mandatory: agent_id, mode, answer, source_claims, user_rules_used, agent_inferences, proposed_actions, risk_decision, execution_result, uncertainties. Source claims require title, URL, retrieval time, and segment/timestamp. User rules require explicit confirmation. Inferences remain separate. Proposed actions are advisory and require central review. risk_decision is informational, not a central risk verdict. execution_result must be null in this release.

## Permission boundary
Specialist permission requests: knowledge.retrieve, user_input.read, chart_attachment.read. NEXUS decides whether to grant them per invocation. No live market/account/position access, position modification, order submission/cancellation, broker credentials, MT5 connectivity, risk-policy modification, or governance bypass is granted.

## Evidence policy
1. Attribute ICT doctrine only when a retrieved source segment supports the claim. Record title, canonical URL, publication date if known, retrieval timestamp, and timestamp/segment identifier.
2. Without evidence, mark attribution unverified; do not fabricate citations.
3. Store user rules only after explicit user statement or confirmation. Never infer risk %, stop placement, entry model, session filter, or exit rule.
4. Keep source claims, user rules, and model inferences in separate output arrays.
5. Do not fabricate chart prices, candle features, session times, fills, or broker state.

## Validation
Install jsonschema>=4.21 and run: python -m unittest discover -s agents/ict_mentor/tests -v
NEXUS must validate inputs and outputs and reject invalid output. Unknown or disabled task types must be rejected before specialist invocation. A schema-valid proposal is never authorization.

## Fail-closed behavior
Missing chart data, missing provenance, ambiguous context, incomplete trade records, or unconfirmed rules produce explicit uncertainty and no fabricated conclusion. Trading or account mutation requests are outside this release and must be referred to central governance.
