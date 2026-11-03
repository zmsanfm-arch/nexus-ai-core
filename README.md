# NEXUS AI CORE

NEXUS AI CORE is a cloud-oriented multi-agent system under active MVP development.

## Release 0.2.0

- FastAPI service and agent registry.
- Deterministic risk classification and approval records.
- Bearer-protected approval decisions.
- OpenAI-compatible model adapter using server-side environment variables.
- Task submission now invokes the configured model and records completed, blocked, or failed status.
- GitHub Actions continuous integration.

## Configure a model

The adapter supports providers exposing an OpenAI-compatible `/chat/completions` endpoint. Configure these variables in the runtime environment or deployment secret manager:

- `MODEL_BASE_URL`: provider API base URL, for example a provider's versioned API root.
- `MODEL_NAME`: exact model identifier from that provider.
- `MODEL_API_KEY`: secret API key; never commit it to Git.
- `MODEL_PROVIDER`: descriptive provider label (optional).
- `MODEL_TIMEOUT_SECONDS`: request timeout (optional, default 45).

Without all three required model settings, task submissions return `blocked`; they do not pretend the model ran.

## Approval administration

Set `NEXUS_ADMIN_TOKEN` and `NEXUS_ADMIN_ID` only in the server-side secret manager. The reviewer identity is derived from server configuration, not from request data.

## API

- `GET /health`
- `GET /agents`
- `POST /tasks`
- `GET /tasks/{task_id}`
- `POST /approvals/{approval_id}/decision` (administrator bearer token required)

## Current limitations

- Storage remains in-memory and is lost on restart.
- The first model adapter is synchronous and single-provider; bounded multi-agent planning, tool execution and durable workflows are not implemented yet.
- The service is not production-ready. Do not expose it publicly before persistent storage, production identity, rate limits, policy enforcement and deployment hardening are completed.

## Local development

```bash
pip install -r requirements.txt
pip install pytest
uvicorn app.main:app --reload
pytest -q
```
