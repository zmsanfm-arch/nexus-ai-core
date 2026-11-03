# NEXUS Web Client API Surface

**Status:** Proposed API contract map. Existing API endpoints remain the only implemented endpoints until separately delivered and tested.

Base path: `/api/v1`. JSON responses. All list endpoints require pagination and stable sorting. All state-changing requests require authenticated actor, authorization, CSRF protection (cookie sessions), idempotency where appropriate, and audit.

## Existing API (repository baseline)

The current backend README documents:
- `GET /health`
- `GET /agents`
- `POST /tasks`
- `GET /tasks/{task_id}`
- `POST /approvals/{approval_id}/decision`

These are current baseline routes, not evidence that the proposed routes below already exist.

## Proposed read endpoints

- `GET /api/v1/system/overview`
- `GET /api/v1/agents`
- `GET /api/v1/agents/{agent_id}`
- `GET /api/v1/strategies`
- `GET /api/v1/strategies/{strategy_id}`
- `GET /api/v1/strategies/{strategy_id}/versions`
- `GET /api/v1/experiments`
- `GET /api/v1/experiments/{experiment_id}`
- `GET /api/v1/backtest-runs`
- `GET /api/v1/backtest-runs/{run_id}`
- `GET /api/v1/backtest-runs/{run_id}/trades`
- `GET /api/v1/demo/accounts`
- `GET /api/v1/demo/accounts/{account_id}/positions`
- `GET /api/v1/demo/accounts/{account_id}/orders`
- `GET /api/v1/demo/accounts/{account_id}/trades`
- `GET /api/v1/risk/policies`
- `GET /api/v1/risk/events`
- `GET /api/v1/approvals`
- `GET /api/v1/audit-events`

## Proposed command endpoints

- `POST /api/v1/strategy-proposals`
- `POST /api/v1/experiments`
- `POST /api/v1/backtest-runs` (NEXUS validates and schedules; client never invokes engine directly)
- `POST /api/v1/strategies/{strategy_id}/transition-requests`
- `POST /api/v1/approvals/{approval_id}/decision`
- `POST /api/v1/demo/operations/{operation_id}/requests` (only after central execution/risk services and Demo controls exist)

No endpoint in the initial UI may expose broker credentials, direct MT5 commands or arbitrary order payloads.

## Common response metadata

Where relevant include:
- `request_id`, `correlation_id`
- `created_at`, `updated_at`
- `environment` (research/demo/live)
- `data_as_of` and `staleness_status`
- `source_refs` and `audit_ref`
- resource `version` / `etag`

## Error semantics

Use stable machine-readable codes such as:
- `UNAUTHENTICATED`
- `FORBIDDEN`
- `VALIDATION_ERROR`
- `NOT_FOUND`
- `CONFLICT`
- `STALE_DATA`
- `DEPENDENCY_UNAVAILABLE`
- `RISK_REJECTED`
- `APPROVAL_REQUIRED`

Never represent unavailable service data as valid zero values. Include field-level validation details without leaking internal stack traces.
