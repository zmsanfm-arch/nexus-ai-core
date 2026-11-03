# NEXUS Specialist Agent Contract — v1

## Ownership boundary

A Specialist Agent owns domain reasoning only. NEXUS AI CORE owns orchestration, identity, authorization, policy enforcement, risk decisions, execution gateways, secrets, and audit.

A specialist must not create a parallel orchestrator, call brokers directly, hold broker credentials, or treat model output as authorization.

## Manifest and permissions

Every specialist declares its ID, name, semantic version, lifecycle status, advisory mode, capabilities, granted permissions, and (where applicable) requested permissions.

Requested permissions are not grants. Central policy must independently allow the capability-to-permission mapping and the manifest must explicitly list the same permission under permissions. ICT Mentor currently has an empty grant list and is disabled.

Malformed manifests and unknown fields are rejected. Disabled agents are discoverable but not dispatchable. Capability declarations do not grant permissions.

## ICT v1 input contract

The central SpecialistInput supports task ID, task type, advisory mode, bounded request text, bounded JSON context, optional chart and trade data, user rules only when status is user_confirmed, retrieved source segments with source ID/title/URL/retrieval time/segment ID, and optional correlation ID.

The specialist receives only the explicit request envelope. It receives no implicit tools, network access, filesystem access, account data, broker credentials, or execution API.

## ICT v1 output contract

The central SpecialistResult requires agent identity, advisory mode, answer, source claims with provenance, separately structured user-confirmed rules and model inferences, structured proposed actions that always require central review, constrained informational risk-decision values, uncertainties, and execution_result structurally fixed to null.

Invalid fields, unrecognized risk decisions, and non-null execution results are rejected.

## ICT Mentor initial scope

- ict.education
- ict.source_lookup
- ict.chart_analysis
- ict.strategy_formalization
- ict.trade_review

Position monitoring, position management, and autonomous execution remain disabled and are not registered as routable capabilities.

## Security invariants

- Disabled means not dispatchable.
- Capabilities are routing metadata, not authorization.
- Requested permissions are not grants.
- Central allowlist and explicit manifest grant must both match.
- Specialist output cannot approve itself, alter policy, or execute an action.
- No broker/MT5 connectivity is exposed through this interface.
- Any future execution path must be a separate central service with deterministic risk checks, authorization, idempotency, audit, and emergency-stop enforcement.
