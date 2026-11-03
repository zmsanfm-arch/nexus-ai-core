# NEXUS AI CORE

NEXUS AI CORE is a cloud-oriented multi-agent system under active MVP development.

## Release 0.3.0

- FastAPI service and agent registry.
- Deterministic risk classification and approval records.
- Bearer-protected approval decisions.
- OpenAI-compatible model adapter using server-side environment variables.
- Durable SQLAlchemy storage for tasks, approvals, and audit events.
- SQLite file storage by default; PostgreSQL-compatible through `DATABASE_URL`.
- GitHub Actions continuous integration.

## Configure a model

The adapter supports providers exposing an OpenAI-compatible `/chat/completions` endpoint. Configure these variables in the runtime environment or deployment secret manager:

- `MODEL_BASE_URL`: provider API base URL.
- `MODEL_NAME`: exact model identifier.
- `MODEL_API_KEY`: secret API key; never commit it to Git.
- `MODEL_PROVIDER`: descriptive provider label (optional).
- `MODEL_TIMEOUT_SECONDS`: request timeout (optional, default 45).

Without all three required model settings, task submissions return `blocked`; they do not pretend the model ran.

## Storage

- Default: `sqlite:///./data/nexus.db` (the directory is created automatically).
- PostgreSQL: set `DATABASE_URL` to a PostgreSQL SQLAlchemy URL when a PostgreSQL service is available.
- Tasks, approvals, and audit events persist across process restarts.
- SQLite is suitable for this single-instance MVP, not concurrent multi-instance production deployment.

## Approval administration

Set `NEXUS_ADMIN_TOKEN` and `NEXUS_ADMIN_ID` only in the server-side secret manager. Reviewer identity is derived from server configuration, not request data.

## API

- `GET /health`
- `GET /agents`
- `POST /tasks`
- `GET /tasks/{task_id}`
- `POST /approvals/{approval_id}/decision` (administrator bearer token required)

## Current limitations

- Model adapter is synchronous and single-provider.
- Bounded multi-agent planning, external tool execution, production identity, rate limits, and durable workflow orchestration are not implemented.
- The service is not production-ready. Do not expose it publicly before deployment hardening and security review.

## Local development

```bash
pip install -r requirements.txt
pip install pytest
uvicorn app.main:app --reload
pytest -q
```
