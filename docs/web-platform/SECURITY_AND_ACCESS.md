# NEXUS Web Platform Security and Access

## Trust boundaries

The browser is an untrusted client. It may render data and submit user intent, but it is never an authority for identity, permissions, risk decisions, approval state or execution state.

All authorization is re-evaluated by NEXUS Core for every request. Hiding a button in the UI is not an authorization control.

## Authentication and sessions

- Use a production identity provider or a hardened server-side authentication service.
- Prefer secure, HttpOnly, SameSite cookies for browser sessions.
- Protect state-changing requests against CSRF.
- Rotate and revoke sessions; enforce expiry and re-authentication for sensitive operations.
- Do not store bearer tokens, broker credentials or model API keys in localStorage/sessionStorage.
- Enforce MFA for administrator and execution-governance roles before any privileged actions are enabled.

## Authorization model

Suggested least-privilege roles (final role mapping remains a central governance decision):
- Viewer: read dashboards and permitted records.
- Researcher: create research requests and draft strategy proposals.
- Reviewer: review experiment/evaluation evidence and submit approval decisions within assigned scope.
- Operator: inspect Demo operations and request permitted operational actions.
- Administrator: manage users and system configuration; cannot bypass Risk Engine controls.
- Auditor: read audit records and compliance exports.

Permissions must be action- and resource-scoped, not just page-scoped. Enforce tenant/account/environment boundaries if multi-user or multi-account support is introduced.

## Secrets and integrations

- Store secrets only in server-side secret manager/environment injection.
- Never return secrets in API payloads, logs, exception messages or UI.
- Browser never connects to broker/MT5 directly.
- Broker connector uses a separate Demo credential set and isolated runtime.
- Live credentials are not configured in the initial release.
- Redact secrets and personal data from structured logs.

## Audit requirements

Record actor, role, action, resource type/ID, decision, reason, timestamp, correlation ID, request ID and before/after references for privileged changes. Audit events should be append-only to application roles; tamper-evidence/retention policy must be designed for production.

## API hardening

- TLS only; strict CORS allowlist.
- CSRF protection for cookie-authenticated writes.
- Rate limits and request size limits.
- Input validation and output filtering.
- Idempotency keys for retryable commands and execution-related requests.
- Pagination and bounded query windows.
- Consistent error envelopes without stack traces.
- Dependency, container and secret scanning in CI.
- Security headers and restrictive Content Security Policy.
- Backups, restore tests, migration discipline and incident response.

## Release gates

No public internet exposure until identity, authorization, CSRF, CORS, rate limiting, secret management, audit, backups, monitoring and security review are complete. No Demo execution UI until the central risk and execution gates exist. Live remains disabled pending a separate release and explicit governance approval.

## Implemented API baseline (current feature branch)

The current API foundation uses server-side bearer credentials as a temporary adapter:
- `NEXUS_ADMIN_TOKEN` plus `NEXUS_ADMIN_ID` grants the administrator role used by approval decisions.
- `NEXUS_API_TOKEN` plus optional `NEXUS_API_ID` grants the operator role for authenticated API access.
- Credentials are compared server-side; identity and role are never accepted from request payloads.
- If neither token is configured, protected routes fail closed with HTTP 503. Missing credentials return 401; invalid credentials and insufficient role return 403.
- `/health` is the only public route and returns minimal liveness information.
- `NEXUS_CORS_ORIGINS` is an explicit comma-separated origin allowlist. An empty value disables cross-origin browser access.
- Baseline response security headers are applied to API responses.

This is a bootstrap authentication adapter, not production identity management. It does not provide user enrollment, MFA, token expiry/rotation, revocation, fine-grained resource scopes, cookie sessions, CSRF protection or rate limiting. Do not expose the API publicly or treat this baseline as a production security sign-off. Replace the adapter with the selected identity provider before public deployment.
