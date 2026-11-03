# Runtime Integration Plan — ICT Mentor on Current NEXUS Main

## Repository snapshot reviewed
The current default branch README describes release 0.4.0 as a bounded sequential Research → Analysis → Auditor pipeline. The implementation files inspected on `main` include:
- `app/services/agent_framework.py`: hard-coded three-agent tuple and sequential invocation.
- `app/services/registry.py`: static registry metadata; no manifest loader or executable specialist registration.
- `app/services/orchestrator.py`: every task is sent to the same generic pipeline.
- `app/schemas.py`: task submission accepts only an objective string.
- `app/services/governance.py`: approval records for a small set of generic sensitive actions; no trade-specific permission/policy model.
- `app/services/risk.py`: keyword-based risk classification, not a deterministic trading risk engine.
- `app/main.py`: current API routes; no specialist task type, market data, positions, or broker gateway.
- `tests/test_agent_framework.py`: tests for the bounded three-agent pipeline.

The README and code version fields are not fully aligned; verify release/version metadata during integration.

## Compatibility finding
The ICT specification branch was created before the latest main changes. Its comparison reports 9 commits ahead and 1 behind, with diverged history. Do not merge it as-is. Reconcile/rebase it onto current main first, preserving the newer central pipeline and tests.

## Minimum safe integration design
1. Keep the existing Research → Analysis → Auditor pipeline intact for generic tasks.
2. Extend task schema with an explicit `task_type` and typed context; default existing clients to the current generic path for backward compatibility.
3. Add a specialist interface with validated input/output contracts and a `run(context)` method. Do not allow specialist prompts or outputs to grant permissions.
4. Add a manifest loader for `agents/*/agent.yaml`; validate schema, unique IDs, declared capabilities, and permission allowlists at startup.
5. Register ICT Mentor as `specification` until the runtime, retrieval, and evaluation gates pass. A manifest alone must not make it executable.
6. Add explicit routing from `ict.*` task types to the ICT specialist. Reject unknown task types; never silently route a trade task to the generic research pipeline.
7. Add a provider-neutral retrieval adapter. Retrieved chunks must carry source title, canonical URL, source type, publication/course metadata where available, and exact timestamp/segment. The model must distinguish official ICT doctrine, user-authored rules, and its own inference.
8. Add an explicit authorization service and versioned user policy for position actions. The generic approval table is not sufficient to authorize broker operations.
9. Keep broker operations outside the specialist. A separate execution gateway must independently re-read account/market/position state, enforce deterministic hard limits and idempotency, apply a kill switch, and write audit events.
10. Add integration tests before enabling the specialist: task routing, schema validation, prompt-injection resistance, source provenance, no permission escalation, stale data rejection, duplicate action rejection, risk rejection, and broker-state reconciliation.

## Explicit non-goals for this stage
- No MT5 credentials or broker API inside the agent process.
- No live orders.
- No claim that the current generic keyword risk classifier is suitable for trading risk.
- No autonomous execution until Demo-only forward testing and a separate security/risk review are complete.

## Current readiness
Design specification only. The inspected `main` code does not yet expose the specialist runtime, task routing, retrieval backend, trading policy model, or execution gateway. The next implementation should begin with backward-compatible task typing and a specialist interface, after branch reconciliation.
