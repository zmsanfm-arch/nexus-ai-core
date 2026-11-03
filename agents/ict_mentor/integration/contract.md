# NEXUS Integration Contract — ICT Mentor

## Current core compatibility

The current NEXUS codebase has:
- FastAPI endpoints for health, agent listing, task submission, task retrieval, and approval decisions.
- An in-memory agent registry with the ids `research`, `analysis`, `developer`, `executor`, and `auditor`.
- A single OpenAI-compatible model adapter.
- A basic orchestrator that sends one generic system prompt to one model.
- SQLAlchemy persistence for tasks, approvals, and audit events.

The current runtime does **not** yet provide a pluggable specialist-agent interface, agent-specific routing, retrieval service, vector store, or multi-agent workflow execution. Therefore this specification intentionally does not pretend that ICT Mentor is already executable.

## Required runtime extension

When the core runtime is ready, add a formal agent interface with at least:

- `agent_id`
- `version`
- `capabilities`
- `permissions`
- `system_prompt`
- `input_schema`
- `output_schema`
- `run(context) -> AgentResult`

The registry should load agent manifests and validate permissions. The orchestrator should route a task to a specialist based on explicit task type/capability, not keyword-only heuristics.

## Proposed task routing

Suggested task types:
- `ict.education`
- `ict.source_lookup`
- `ict.chart_analysis`
- `ict.strategy_formalization`
- `ict.trade_review`

Suggested assignment:
- `ict_mentor` handles education, source lookup, chart interpretation, and strategy review.
- A separate market-data/chart agent may provide normalized OHLCV and session data later.
- The Forex execution agent, if added later, remains separate and must not inherit broker permissions from ICT Mentor.

## Retrieval boundary

The ICT Mentor should call a retrieval interface such as:

```python
retrieve(
    query: str,
    filters: dict,
    top_k: int = 6,
) -> list[KnowledgeChunk]
```

Each `KnowledgeChunk` must include source metadata and timestamps. The agent may not fabricate a citation when retrieval returns no supporting chunk.

The storage backend is intentionally undecided. Keep the interface provider-neutral so the core can choose PostgreSQL + pgvector or another supported retrieval store later.

## Output schema (proposed)

```json
{
  "agent_id": "ict_mentor",
  "answer": "string",
  "source_claims": [
    {
      "claim": "string",
      "source_id": "string",
      "title": "string",
      "url": "string",
      "timestamp_start": "string",
      "timestamp_end": "string"
    }
  ],
  "user_rules_used": ["string"],
  "agent_inferences": ["string"],
  "uncertainties": ["string"],
  "risk_note": "advisory_only"
}
```

## Security and governance

- Register only read/research/analysis permissions.
- No broker credentials or trading execution tools are exposed to this agent.
- Agent output is untrusted data and never authorizes an action.
- All consequential actions remain subject to the independent NEXUS governance and risk controls.
- Keep provider keys and database credentials in server-side environment variables/secrets, never in manifests or prompts.

## Acceptance tests before runtime registration

1. Registry loads the manifest and reports `ict_mentor` as available.
2. Task router sends `ict.education` to ICT Mentor.
3. Retrieved source claims include valid URLs and timestamps.
4. Unsupported attribution is explicitly marked unverified.
5. User-defined strategy rules remain separate from ICT source doctrine.
6. The agent cannot invoke broker or execution capabilities.
7. Missing model configuration or retrieval service fails closed with an explicit blocked status.
8. All task and retrieval operations are auditable.
