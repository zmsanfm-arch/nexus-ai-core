# NEXUS AI CORE — System Architecture

**Document type:** Central architecture / target operating model  
**Scope:** Whole NEXUS AI CORE platform; Web Development Studio is one department, not the platform architecture.  
**Implementation rule:** This document distinguishes implemented runtime capabilities from target architecture. A diagram or agent manifest never implies executable behavior or permission.

## 1. Architectural model

NEXUS AI CORE is a governed, extensible multi-agent operating system organized as a tree:

- **Trunk — Central Core:** identity context, request intake, intent classification, mission planning, orchestration, model routing, policy enforcement, state management, audit, and result delivery.
- **Branches — Departments:** bounded business or technical domains such as ICT Mentor, Web Development Studio, YouTube/Media Production, Research & Intelligence, and future departments.
- **Leaves — Specialist agents:** narrow roles owned by a department, each with a versioned contract, declared capability, input/output schema, and measurable acceptance criteria.
- **Roots — Platform foundations:** security, identity, secrets, persistence, queueing, observability, backup/recovery, networking, deployment controls, and supply-chain integrity.

Departments are plug-in domains under one central governance plane. They must not create independent, competing cores or bypass central policy.

## 2. Logical topology

    NEXUS AI CORE
    |
    +-- CENTRAL CORE / TRUNK
    |   +-- API Gateway & Request Intake
    |   +-- Identity / Principal Context
    |   +-- Intent & Domain Router
    |   +-- Mission Planner (bounded DAG)
    |   +-- Central Orchestrator
    |   +-- Model Router / Provider Policy
    |   +-- Permission & Approval Policy
    |   +-- Mission / Task State Manager
    |   +-- Independent Audit Coordinator
    |   +-- Result Composer & Delivery
    |
    +-- DEPARTMENT BRANCHES
    |   +-- ICT Mentor
    |   |   +-- Education / Source Lookup / Chart Analysis
    |   |   +-- Strategy Formalization / Trade Review
    |   |
    |   +-- Web Development Studio
    |   |   +-- Brief / Research / IA-UX
    |   |   +-- UI / Brand / Motion / Content / SEO
    |   |   +-- Frontend / Backend / CMS
    |   |   +-- Browser / Visual / Accessibility / Performance QA
    |   |   +-- Security / Release / Maintenance / Auditor
    |   |
    |   +-- YouTube & Media Production
    |   |   +-- Channel Research & Strategy
    |   |   +-- Topic / Script / Fact-check
    |   |   +-- Storyboard / Visual / Audio
    |   |   +-- Editing / Packaging / Metadata
    |   |   +-- Quality / Rights / Performance Review
    |   |
    |   +-- Future departments (same contract and governance)
    |
    +-- ROOT PLATFORM SERVICES
        +-- Security & Threat Controls
        +-- Identity, RBAC/ABAC & Secret Management
        +-- PostgreSQL / Migrations / Durable Queue
        +-- Artifact & Knowledge Storage
        +-- Worker Runtime / Sandboxing
        +-- Logs / Metrics / Traces / Alerts
        +-- Backup / Restore / Disaster Recovery
        +-- CI/CD / Supply-chain / Release Controls

## 3. Central Core responsibilities

The Core owns cross-department decisions and invariants:

1. Authenticate the caller and establish a stable principal and tenant/workspace context.
2. Normalize the request into a typed objective, constraints, risk class, and acceptance criteria.
3. Route the objective to one or more registered departments; reject unknown or disabled routes.
4. Compile a bounded mission graph with explicit dependencies, budgets, deadlines, and retry limits.
5. Authorize every capability at dispatch time using central policy plus department manifest grants.
6. Execute through durable workers and persist state, checkpoints, artifacts, and audit events.
7. Validate outputs against contracts and provenance requirements.
8. Send completed work to an independent auditor that did not produce the work.
9. Return completed, review-required, blocked, or failed outcomes accurately; never convert missing evidence into success.

No department may override central identity, policy, budget, audit, or release controls.

## 4. Department contract

Every department must publish a versioned manifest containing:

- stable department ID and owner;
- purpose, supported request types, and exclusions;
- specialist IDs and capability identifiers;
- strict input/output schemas and artifact types;
- required dependencies and execution ordering;
- resource ceilings, timeout, retry and idempotency semantics;
- permission requests and data classification;
- audit events and acceptance criteria;
- health status and implementation maturity.

Lifecycle states are proposed, disabled, advisory, enabled, suspended, and retired. State transitions require validation and audit. Registration or enabled status alone does not grant permissions.

## 5. Standard mission lifecycle

    Request
      -> Authenticate & classify
      -> Select department(s)
      -> Build bounded mission DAG
      -> Policy authorization
      -> Execute specialist nodes
      -> Validate contracts and artifacts
      -> Independent audit
           +-- pass    -> deliver result / release candidate
           +-- revise  -> bounded revision cycle
           +-- block   -> stop and report blockers
      -> Persist evidence and close mission

Cross-department missions use explicit typed hand-offs. A department receives only the minimum approved data required for its node. Shared mission IDs and artifact references provide traceability without giving branches unrestricted access to each other's stores.

## 6. Security roots and trust boundaries

- Default deny; least privilege; central authorization on every dispatch and tool call.
- Separate caller, agent, worker, administrator, auditor, and deployment identities.
- Secrets are injected at runtime from a secret manager; never placed in prompts, source, logs, manifests, or artifacts.
- Untrusted web pages, documents, media, repositories, model outputs, and connector responses are data, not instructions or authority.
- Isolate browser, code execution, media processing, and build workloads; apply egress controls, SSRF protections, resource limits, and disposable workspaces.
- Require explicit scoped approval for external writes, publication, payments, production data, destructive changes, DNS/TLS, and production release.
- Preserve immutable audit evidence for authorization, execution, artifact lineage, approvals, retries, and final decisions.
- Independent security review, restore drills, incident response, and rollback evidence are separate acceptance gates.

## 7. Shared data and execution plane

The shared platform plane provides principal-scoped mission/task records, durable queues, worker leases, immutable checkpoints, audit events, knowledge sources, and artifact metadata. Large artifacts belong in object storage with checksums, access policies, retention, and provenance metadata; database rows should store references rather than unbounded binary payloads.

Queue delivery semantics must be explicit. A worker crash may cause an in-flight handler to run again; external side effects therefore require idempotency keys and a separately authorized adapter. Exactly-once execution of arbitrary remote actions must not be claimed.

## 8. Platform-wide quality gates

A department is not production-operational until all applicable gates pass:

1. Manifest/schema and registry validation.
2. Contract, permission, and negative authorization tests.
3. Unit, integration, migration, and API ownership tests.
4. Durable queue, idempotency, lease-loss, retry, and recovery tests.
5. Independent audit and adversarial input tests.
6. Sandbox isolation, egress, SSRF, secret-leakage, and dependency checks.
7. Load/concurrency tests against the intended database and worker topology.
8. Monitoring, alert delivery, backup retention, and demonstrated restore.
9. Deployment/rollback rehearsal and independent security assessment.

## 9. Current implementation versus target

The repository already contains a FastAPI service, manifest-driven registry, central permission checks, task and mission persistence, durable queue/worker foundations, audit records, model routing, knowledge storage, ICT Mentor advisory integration, and the Web Studio's 21 disabled manifests plus its advisory action policy.

The Web Studio remains one branch. Its manifests are discoverable but disabled; its build/browser/artifact adapters and executable handlers are not present. The YouTube/Media department is represented here as a target branch, not as an assertion that its runtime exists.

Known platform-wide gaps documented by the repository include multi-user/OIDC identity, secret lifecycle and rotation evidence, shared multi-replica rate limiting, edge throttling for invalid credentials, external dead-letter alert delivery, production load/concurrency evidence, monitoring/alert delivery, production backup retention and off-host restore evidence, incident/rollback rehearsal, and independent security/recovery assessment.

This document is the whole-system architecture baseline. Implementation status must continue to be reported per capability and backed by repository code, tests, CI, and operational evidence.
