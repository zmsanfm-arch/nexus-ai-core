# NEXUS AI CORE — Mission Workflows

## Purpose

A mission is a user-defined objective represented as a bounded directed acyclic graph (DAG). It describes which registered agents participate, which outputs they depend on, and the maximum number of attempts allowed.

The mission contract is declarative. Validation and compilation do **not** execute agents, connect external services, grant permissions, or publish content.

## Current contract

A mission contains:

- `mission_id`: stable identifier.
- `name`: human-readable name.
- `objective`: bounded user-provided objective.
- `nodes`: one to 32 workflow nodes.
- `max_total_attempts`: total planned invocation budget, capped at 64.
- `approval_policy`: currently fixed to `required_for_external_actions`.

Each node contains a unique `node_id`, a registered `agent_id`, an explicit `capability`, dependency IDs, and a per-node attempt ceiling. The compiler rejects duplicate IDs, unknown dependencies, cycles, unregistered agents, and budget overruns.

Registration is not authorization. The runtime separately verifies the agent's enabled status, capability grant, central permission policy, and installed handler before invoking it.

## Example: YouTube channel research

This example is deliberately limited to research and planning. It does not claim that the current repository can access YouTube analytics, inspect live trends, generate video assets, or publish videos.

```yaml
mission_id: youtube_channel_research
name: YouTube channel research and content plan
objective: >
  Evaluate supplied channel examples and reference videos.
  Produce a source-qualified content strategy and a testable publishing plan.
max_total_attempts: 3
approval_policy: required_for_external_actions
nodes:
  - node_id: research
    agent_id: research
    capability: research.read
  - node_id: analysis
    agent_id: analysis
    capability: analysis.review
    dependencies: [research]
  - node_id: audit
    agent_id: auditor
    capability: audit.review
    dependencies: [analysis]
```

## Intended execution lifecycle

1. User creates a mission and defines the objective, success criteria, constraints, budget, and permitted resources.
2. Core validates the mission schema, graph, registered agents, permissions, and resource ceilings.
3. Planner creates a deterministic topological execution plan.
4. Current runtime executes eligible nodes sequentially; parallel execution is not implemented.
5. Each agent receives only the minimum task context and explicitly granted capabilities.
6. Results are schema-validated, size-bounded, and audited.
7. A separately injected independent auditor validates the combined outputs. Only a valid `pass` verdict permits status `completed`; `revise` returns `review_required`, `block` returns `blocked`, and auditor errors return `audit_failed`. Without an auditor, status remains `nodes_succeeded` and is not mission completion.
8. External actions (for example, uploading or publishing a video) require a separate connector, scoped credentials, explicit policy authorization, and approval where configured.
9. The mission records outcome metrics and provenance so later runs can improve without rewriting historical evidence.

## Required controls before autonomous execution

- Per-agent capability allowlists and least-privilege connector scopes.
- Secret storage outside mission definitions and prompts.
- Explicit approval gates for publishing, spending, account changes, and irreversible actions.
- Per-mission limits for model calls, retries, wall-clock time, and external API usage.
- Idempotency keys and duplicate-action prevention.
- Audit events for planning, dispatch, tool calls, approvals, revisions, and final outcomes.
- Cancellation, timeout, failure recovery, and dead-letter handling.
- Evaluation datasets and quality thresholds for each mission type.

## Current implementation boundary

Mission definitions can now be submitted through authenticated `POST /missions` and read through principal-scoped `GET /missions/{mission_id}`. Definitions are schema-validated, checked against registered advisory agents and each agent's declared capability grants, and persisted in the SQL database using migration `0004_missions`. A mission ID is unique; reads by another principal return not found. These endpoints only define and retrieve missions: they do not enqueue or execute them. The API explicitly returns `execution_available: false` until a durable execution coordinator and correctly wired specialist/auditor handlers are implemented.

The current increment adds a sequential advisory-only mission runtime for installed specialist handlers. It checks registered/enabled agent state, declared capability, central permission policy, and handler presence before each node; it passes only completed dependency outputs, bounds specialist output to 16 KiB, and applies bounded per-node attempts. A separately injected auditor receives the bounded combined output and must return a strict `pass`, `revise`, or `block` verdict. Only `pass` yields `status: completed`; missing auditor leaves `nodes_succeeded`, and invalid or failed audit returns `audit_failed`. No connector, credentials, external-action API, or publishing interface is exposed. Dynamic routing, parallel scheduling, persistent mission definitions, UI management, external connectors, media generation, and autonomous publishing remain unimplemented.


## Durable mission execution

Mission definitions can be submitted to the dedicated durable run queue with
`POST /missions/{mission_id}/runs` and a caller-generated
`Idempotency-Key` header. Repeated submissions for the same principal,
mission, and key return the original run rather than enqueueing another run.
Run status and per-node checkpoints are available through
`GET /missions/{mission_id}/runs/{run_id}`; reads remain principal-scoped.

The `mission_runs`, `mission_node_runs`, and `mission_queue` tables persist
run state, per-node status/output/attempt count, and worker leases. Workers
claim rows transactionally with `FOR UPDATE SKIP LOCKED`. An expired lease
makes a run claimable again. A recovered worker skips nodes with durable
`completed` checkpoints and continues from unfinished nodes. Lease ownership
is checked on checkpoint and completion writes, so a stale worker cannot
overwrite a newer worker's state.

Execution is **at-least-once** for an in-flight handler: a process crash after
the handler returns but before its checkpoint commits can cause that handler
to be called again after lease recovery. Run enqueue is idempotent and
completed node checkpoints are not repeated; exactly-once execution of an
arbitrary remote/model call cannot be guaranteed by a database transaction.
Handlers must therefore remain advisory and tolerate retries.

The mission worker service is a separate process and must be deployed and
supervised against the same PostgreSQL database before queued runs will
progress. The API can durably accept and report runs even while no worker is
available. This worker has no external-action, publishing, payment, broker,
or credential interface. Human approval remains mandatory for any future
external action implementation.
