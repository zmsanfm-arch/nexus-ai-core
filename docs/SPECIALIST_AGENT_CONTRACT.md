# NEXUS Specialist Agent Contract — v1

## Ownership boundary

A Specialist Agent owns domain reasoning only. NEXUS AI CORE owns orchestration, identity,
authorization, policy enforcement, risk decisions, execution gateways, secrets, and audit.

A specialist must not create a parallel orchestrator, call brokers directly, hold broker
credentials, or treat model output as authorization.

## Manifest

Every specialist declares:
- `agent_id`, `name`, semantic `version`
- lifecycle `status` (`registered` or `disabled`)
- `mode` (currently advisory only)
- explicit `capabilities`
- explicit `permissions` (empty by default)

Unknown fields and malformed manifests are rejected. Disabled agents are discoverable but
must not be dispatched. Capability declarations do not grant permissions.

## Runtime contract

`SpecialistInput` contains a task ID, task type, and bounded context.
`SpecialistResult` separates source claims, documented user rules, model inferences,
proposed actions, uncertainties, and risk status. Execution result is always null in this
contract version.

The `SpecialistAgent` protocol exposes `run(request) -> SpecialistResult`. It does not
provide tools, network access, filesystem access, or execution APIs.

## ICT Mentor initial registration

ICT Mentor is registered as disabled and advisory-only. Initial capabilities:
- `ict.education`
- `ict.source_lookup`
- `ict.chart_analysis`
- `ict.strategy_formalization`
- `ict.trade_review`

Position monitoring, position management, and autonomous execution are intentionally
omitted until separately designed, authorized, and tested.

## Security invariants

- Disabled means not dispatchable.
- Capabilities are routing metadata, not authorization.
- Empty permissions mean no granted operational permissions.
- Every specialist dispatch must pass the central `PermissionService`: the capability must
  map to a core-owned permission, that permission must be in the core allowlist, and the
  agent manifest must explicitly declare the same permission. Unknown capabilities fail closed.
- Specialist output cannot approve itself or change policy.
- No broker/MT5 connectivity is exposed through this interface.
- Any future execution path must be a separate central service with independent deterministic
  risk checks, authorization, idempotency, audit, and kill-switch enforcement.
