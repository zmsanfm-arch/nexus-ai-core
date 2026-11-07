# Controlled self-extension

## Goal

NEXUS agents may identify capability gaps and draft reusable tools, skills, and
plugin manifests. This is a proposal workflow, not unrestricted self-modifying
software.

## Lifecycle

1. **Discover**: an agent describes the missing capability and its intended use.
2. **Specify**: it supplies a structured tool schema, skill instructions, or
   plugin metadata.
3. **Generate**: CapabilityProposalFactory serializes a declarative artifact.
4. **Validate**: Pydantic and JSON Schema validation reject malformed definitions.
5. **Review**: central Governance evaluates provenance, scope, requested
   permissions, dependencies, risk, tenant scope, and compatibility.
6. **Approve**: an authorized principal or explicitly delegated core policy
   approves the exact artifact version and permission set.
7. **Sandbox test**: tests run in an isolated worker with resource limits,
   restricted network access, no host secrets, and audit capture.
8. **Activate**: the core lifecycle service enables the exact approved version.
9. **Monitor/revoke**: runtime use is audited and can be disabled or revoked.

## Non-negotiable boundaries

- Generated tools, skills, and plugins are disabled by default.
- A plugin's requested permissions are informational; generated manifests
  contain no granted permissions.
- Agents cannot approve their own proposals or expand the core permission
  allowlist.
- Tool schemas are data contracts; schema validation does not execute tools.
- Skill instructions are untrusted instruction data and cannot override core
  policy or system instructions.
- No dynamic imports, package installation, shell execution, hot reload, or
  automatic repository writes are provided by the proposal factory.
- Activation must be a separate audited core operation after authorization.
- Existing central Governance, PermissionService, Risk Engine, Audit, and
  Execution Gateway remain authoritative.

## Current implementation boundary

`app/services/capability_factory.py` creates validated YAML proposals for
tools, skills, and plugin manifests. It does not persist, install, execute,
approve, or activate them. The next integration stages are proposal storage,
review APIs, audit events, signed artifact provenance, sandbox testing, and
core-controlled lifecycle activation.
