# NEXUS Integration Contract — ICT Mentor

## Current core compatibility

The current NEXUS codebase has FastAPI endpoints, an agent registry, a single OpenAI-compatible model adapter, a basic orchestrator, and SQLAlchemy persistence for tasks, approvals, and audit events.

The current runtime does **not** yet provide a pluggable specialist-agent interface, agent-specific routing, retrieval service, vector store, or broker execution gateway. This specification does not claim ICT Mentor is already executable.

## Required runtime extension

Add a formal agent interface with:
- `agent_id`, `version`, `capabilities`, `permissions`
- `system_prompt`, `input_schema`, `output_schema`
- `run(context) -> AgentResult`

The registry loads manifests and validates permissions. The orchestrator routes by explicit task type/capability.

## Operating modes and authorization

1. **Advisory (default):** research, retrieval, analysis, and proposals only.
2. **Position management:** read/modify/close only positions explicitly covered by an approved policy.
3. **Autonomous execution:** submit/manage orders only within a user-approved, versioned strategy and hard limits.

Mode changes must be explicit, authenticated, auditable, and performed outside the model. A model prompt or model-generated response cannot activate permissions.

## Execution architecture

ICT Mentor must never hold broker credentials or call MT5/broker APIs directly. It submits a typed action request to a separate NEXUS Execution Gateway.

The gateway must:
- Authenticate the requesting agent and verify its current permissions.
- Validate the action against the active user-approved policy.
- Fetch current account, market, and position state independently.
- Run deterministic risk checks immediately before execution.
- Enforce instrument/account scope, max risk per trade, max aggregate exposure, max position count, daily loss, drawdown, spread, slippage, trading hours, and kill-switch state.
- Reject stale data, duplicate requests, invalid stops/targets, and inconsistent broker state.
- Use idempotency keys and reconcile broker acknowledgements and final position state.
- Persist a complete audit record for each proposed, approved, rejected, and executed action.

## Initial rollout

- Keep execution disabled by default.
- Build and test on Demo only.
- Begin with read-only position monitoring, then explicitly authorized position management, then bounded autonomous execution.
- Do not enable a live account without a separate user decision, security review, and evidence from Demo forward-testing.
- The risk engine must remain able to block any action, regardless of the agent's recommendation or mode.

## Proposed task routing

- `ict.education`
- `ict.source_lookup`
- `ict.chart_analysis`
- `ict.strategy_formalization`
- `ict.trade_review`
- `ict.position_monitoring`
- `ict.position_management`
- `ict.autonomous_execution`

## Retrieval boundary

Use a provider-neutral interface:

```python
retrieve(query: str, filters: dict, top_k: int = 6) -> list[KnowledgeChunk]
```

Every chunk includes source metadata and timestamps. The agent may not fabricate citations.

## Proposed output schema

```json
{
  "agent_id": "ict_mentor",
  "mode": "advisory",
  "answer": "string",
  "source_claims": [],
  "user_rules_used": [],
  "agent_inferences": [],
  "proposed_actions": [],
  "risk_decision": "not_requested",
  "execution_result": null,
  "uncertainties": []
}
```

## Acceptance tests

1. Registry loads the manifest and routes ICT task types correctly.
2. Default mode cannot invoke execution tools.
3. Mode changes require authenticated, auditable user authorization.
4. Agent cannot expand its own permissions.
5. Every proposed action is independently checked by the risk engine.
6. Stale data, duplicate requests, risk breaches, and kill-switch activation fail closed.
7. Broker results are reconciled and audited; no success is claimed without acknowledgement.
8. Source claims have valid links/timestamps; unsupported attribution is marked unverified.
9. User strategy rules remain separate from ICT source doctrine.
