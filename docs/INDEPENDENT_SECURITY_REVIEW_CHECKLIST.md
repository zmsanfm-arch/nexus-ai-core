# Independent security review sign-off

This checklist is an evidence pack for an assessor who did not implement this PR. CI scans and author self-review do not satisfy this sign-off.

## Scope

- [ ] Threat model covers the NEXUS Core control plane, mission queue/leases, role registry, permission service, and advisory output validation.
- [ ] Verify all 21 Web Studio role manifests remain disabled and have no permissions; verify task capability confusion and principal spoofing are rejected.
- [ ] Review Docker build context validation, base-image digest allowlist, network-disabled build execution, resource limits, and Docker daemon trust boundary.
- [ ] Review remote Docker daemon mutual TLS, host isolation, daemon authorization, image provenance, and absence of a Docker socket in application containers.
- [ ] Review ephemeral browser network creation/cleanup, internal-network isolation, exclusive proxy membership, external default-route verification, and concurrent-run isolation.
- [ ] Review HTTPS CONNECT parsing, domain boundary checks, DNS resolution, public-IP validation, DNS-rebinding resistance, redirects, WebSockets, and proxy denial behavior.
- [ ] Review browser container hardening: non-root UID, read-only root filesystem, dropped capabilities, no-new-privileges, seccomp defaults, PID/CPU/memory/time limits, and artifact output bounds.
- [ ] Review artifact store principal isolation, atomic writes, content hashes, archive path validation, symlink/hardlink rejection, and backup key separation.
- [ ] Review retry/lease-loss behavior, idempotency, audit integrity, and failure recovery.
- [ ] Review PostgreSQL transaction/locking behavior, pool exhaustion, and concurrent worker claims.
- [ ] Review monitor webhook authentication, TLS, failure handling, and alert thresholds.

## Evidence to inspect

- Current PR-head CI run and complete job logs.
- Real Playwright container E2E result and screenshot/report artifact metadata.
- PostgreSQL concurrent enqueue/claim stress result.
- Encrypted PostgreSQL backup/restore drill result.
- Encrypted mission artifact-volume backup/restore drill result.
- Browser egress proxy container image digest and runtime network inspection output.
- Remote Docker daemon mTLS configuration and host firewall/authorization policy.

## Findings and sign-off

- Reviewer identity:
- Review date:
- Commit SHA reviewed:
- Critical findings:
- High findings:
- Medium findings:
- Low findings:
- Required remediations:
- Retest evidence:
- Final decision: **Not reviewed / Changes requested / Approved**

Do not mark the review approved until the reviewer records a commit SHA and verifies the live CI evidence. Do not merge this PR based on this checklist alone.
