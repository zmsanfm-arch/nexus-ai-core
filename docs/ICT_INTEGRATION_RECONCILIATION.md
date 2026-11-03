# ICT Mentor Integration Reconciliation

## Source of truth and branch safety

The Forex/ICT workstream has delivered a specialist specification on
`feature/ict-mentor-agent-foundation` (PR #1). It is not an independently
deployable agent. The central runtime remains owned by NEXUS AI CORE.

At review time, the ICT branch is 49 commits ahead and 1 behind `main`,
while the central specialist-runtime branch is 28 commits ahead and 0 behind.
The branches have different merge bases. PR #1 also modifies central files
(`app/main.py`, `tests/test_api_security.py`, and CI configuration).
Do not merge PR #1 wholesale or rebase it blindly onto the central runtime.

## Accepted ICT scope

The initial advisory capabilities are:

- `ict.education`
- `ict.source_lookup`
- `ict.chart_analysis`
- `ict.strategy_formalization`
- `ict.trade_review`

The following remain disabled and must not be registered as routable:

- `ict.position_monitoring`
- `ict.position_management`
- `ict.autonomous_execution`

ICT Mentor has no broker/MT5 connection, account or position access, order
submission/cancellation, credential access, risk-policy modification, or
governance bypass. Its `execution_result` must always be null.

## Contract reconciliation required

The Forex branch defines canonical JSON Schema contracts at:

- `agents/ict_mentor/schemas/input.schema.json`
- `agents/ict_mentor/schemas/output.schema.json`

The central branch currently uses Pydantic `SpecialistInput` and
`SpecialistResult` models. Their envelope and field types are not yet fully
equivalent to the Forex schemas:

- Forex output source claims carry source IDs, segment IDs, URLs and retrieval
  timestamps; central `SourceClaim` currently uses a reduced shape.
- Forex user rules, inferences and proposed actions are structured objects;
  central currently models these as strings.
- Forex risk-decision values are a constrained advisory vocabulary; central
  currently accepts an unrestricted string.
- Forex input uses `task_type`, `mode`, `request` and optional provenance,
  chart, trade and confirmed-rule fields; central currently wraps task ID,
  task type and a generic bounded context.

Do not enable the ICT manifest until the central models validate the Forex
contracts (or a documented, tested adapter performs a lossless translation).
Reject unknown fields and invalid outputs. Preserve provenance and keep source
claims, user-confirmed rules and model inferences separate.

## Permission reconciliation

The Forex manifest lists `knowledge.retrieve`, `user_input.read` and
`chart_attachment.read` as requested permissions, not grants. Central policy
must decide per invocation. These names must not be treated as equivalent to
the current central internal `ict.advisory.*` permission labels without an
explicit mapping and tests.

The current central ICT manifest is disabled and has an empty permission list.
This is intentional fail-closed behavior. No permission is granted by this
document.

## Safe integration sequence

1. Keep PR #1 unmerged; do not import its changes to central auth, API,
   orchestrator, storage or CI wholesale.
2. Port only ICT-owned specialist assets: prompt, schemas, examples,
   source-record schema and domain tests.
3. Implement and test a lossless adapter between the Forex schema and the
   central specialist envelope, including provenance and correlation IDs.
4. Map requested read permissions to explicit central permission identifiers;
   require both central allowlisting and per-agent declaration.
5. Add a concrete advisory-only handler with no implicit network, filesystem,
   broker or MT5 tools.
6. Keep the manifest disabled until schema tests, runtime tests, authorization
   tests and CI all pass.
7. Enable only after independent review; never infer permission from a
   capability name or model output.

## Ownership boundaries

NEXUS CORE owns authentication, identity, task lifecycle, routing, permission
decisions, audit, approvals, risk, execution, service lifecycle and deployment.
ICT Mentor owns domain reasoning and structured advisory output only.
Backtesting and the web control plane remain separate future workstreams.
