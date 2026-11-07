# OpenClaw-inspired capability assessment and integration boundary

## Purpose

This branch evaluates reusable architectural patterns from OpenClaw without embedding,
vendoring, or making NEXUS dependent on OpenClaw. NEXUS core, central Governance,
PermissionService, Risk Engine, audit trail, and execution boundaries remain authoritative.

## Patterns worth adopting

1. Capability separation: callable tools, reusable skill instructions, and installable runtime integrations remain distinct.
2. Metadata-first plugin catalog: discover and validate manifests without importing or executing plugin code.
3. Explicit permission intersection: core allowlist and plugin declared grant must both authorize an exact action.
4. Gateway as control plane: route requests through the core; adapters cannot bypass governance.
5. Session isolation: scope history, artifacts, and memory by principal, agent, and session; cross-agent reads require explicit policy.
6. Pairing and idempotency: remote nodes/channels need explicit enrollment, authenticated transport, replay-safe request IDs, and audited revocation.
7. Untrusted-input handling: messages, web pages, attachments, and tool output remain data, never instructions overriding core policy.

## Implemented in this branch

- app/services/plugin_registry.py: strict metadata-only manifest parsing, duplicate detection, read-only discovery, and fail-closed permission intersection.
- tests/test_plugin_registry.py: validation, duplicate IDs, disabled plugins, and permission escalation tests.
- app/services/capability_catalog.py: declarative tool and skill contracts with JSON Schema validation.
- app/services/capability_factory.py: controlled self-extension proposal generation for tools, skills, and plugin manifests; outputs remain disabled and inert.
- tests/test_capability_catalog.py and tests/test_capability_factory.py: catalog and self-extension validation coverage.
- docs/CONTROLLED_SELF_EXTENSION.md: proposal-to-activation lifecycle and security boundaries.

## Deliberately not implemented or enabled

- No dynamic imports, package installation, entrypoint execution, hot reload, or third-party code execution.
- No messaging credentials, external network connections, or channel activation.
- No browser execution or host command tools are granted to plugins.
- No change to MT5, broker connectivity, order execution, or trading permissions.
- No change to Main and no merge.

## Remaining engineering work before runtime activation

1. Add durable proposal storage, review APIs, and audit events for every lifecycle transition.
2. Add signed/verified package provenance and dependency pinning.
3. Define versioned tool/provider/channel interfaces and compatibility checks.
4. Add isolated worker/container execution with resource and network policies.
5. Bind plugin permissions to tenant/principal and resource scopes.
6. Add secret references that never expose values to agents or logs.
7. Add lifecycle controls (install, enable, disable, revoke) with audit events.
8. Enforce session ownership and visibility policy for agent-to-agent access.
9. Add integration, abuse-case, dependency, and sandbox escape tests.

## Upstream references

- https://docs.openclaw.ai/architecture
- https://docs.openclaw.ai/tools
- https://docs.openclaw.ai/gateway/security
- https://docs.openclaw.ai/gateway/protocol
- https://docs.openclaw.ai/concepts/multi-agent