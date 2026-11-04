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

Each node contains a unique `node_id`, a registered `agent_id`, dependency IDs, and a per-node attempt ceiling. The compiler rejects duplicate IDs, unknown dependencies, cycles, unregistered agents, and budget overruns.

Registration is not authorization. A future runtime must separately verify the agent's enabled status, capability grants, central permission policy, installed handler, and mission-level action policy before invoking it.

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
  - node_id: analysis
    agent_id: analysis
    dependencies: [research]
  - node_id: audit
    agent_id: auditor
    dependencies: [analysis]
```

## Intended execution lifecycle

1. User creates a mission and defines the objective, success criteria, constraints, budget, and permitted resources.
2. Core validates the mission schema, graph, registered agents, permissions, and resource ceilings.
3. Planner creates a deterministic topological execution plan.
4. Scheduler runs only nodes whose dependencies have completed; independent nodes may be parallelized only by a separately bounded scheduler.
5. Each agent receives only the minimum task context and explicitly granted capabilities.
6. Results are schema-validated, persisted, and audited.
7. An independent reviewer checks the result. Revision is bounded; unresolved findings block completion.
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

The current increment supplies strict mission validation and DAG compilation only. Dynamic mission execution, parallel scheduling, persistent mission definitions, UI management, external connectors, media generation, and autonomous publishing remain unimplemented. The core must not represent a mission as executed or completed until those capabilities exist and their independent safety checks pass.
