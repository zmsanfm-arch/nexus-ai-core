# NEXUS Integration Contract — ICT Mentor (Advisory Release)

## Ownership boundary
ICT Mentor is a specialist invoked only by the NEXUS central orchestrator. It must not implement an orchestrator, task manager, scheduler, permission service, risk engine, audit service, MT5 connector, broker adapter, or execution gateway. NEXUS owns authentication, authorization, routing, approvals, audit, market-data access, risk decisions, and any future execution.

## Active task types
- ict.education
- ict.source_lookup
- ict.chart_analysis
- ict.strategy_formalization
- ict.trade_review

## Defined but disabled task types
- ict.position_monitoring
- ict.position_management
- ict.autonomous_execution

The disabled task types must be rejected before specialist invocation in this release.

## Mode
Only advisory mode is supported. Any other mode is rejected. The specialist cannot change its mode or permissions. A chart-analysis or trade-review request is not authorization to trade.

## Permissions
Specialist permission requests are limited to knowledge.retrieve, user_input.read, and chart_attachment.read. NEXUS grants permissions per invocation. ICT Mentor receives no market/account/position access, position modification, order submission/cancellation, broker credentials, MT5 connectivity, risk-policy modification, or governance-bypass permission.

## Input and output
The canonical JSON Schemas are in schemas/input.schema.json and schemas/output.schema.json. The output requires agent_id, mode, answer, source_claims, user_rules_used, agent_inferences, proposed_actions, risk_decision, execution_result, and uncertainties. execution_result is always null in this release. source_claims require source title, valid URL, retrieval time, and segment/timestamp provenance. User rules must be explicitly confirmed by the user. Inferences must remain separate.

## Evidence policy
ICT doctrine claims require retrieved source evidence. Each claim must identify title, canonical URL, retrieval timestamp, and segment/timestamp. If evidence is absent, mark the claim unverified; do not fabricate citations or attribution. Personal rules are recorded only after explicit user statement or confirmation. Do not invent entry, exit, session, invalidation, or risk rules.

## Fail-closed policy
Missing chart evidence, incomplete trade data, missing source provenance, ambiguous context, or unconfirmed rules must be surfaced as uncertainty. The specialist must not fabricate prices, candle structure, fills, broker state, or source timestamps. Trading/account mutation requests are out of scope and must be referred to central governance.

## Validation
Run the schema tests with jsonschema>=4.21:
python -m unittest discover -s agents/ict_mentor/tests -v

NEXUS must validate input/output and reject unknown or disabled task types before invoking the specialist. Schema-valid proposals are not authorization.
