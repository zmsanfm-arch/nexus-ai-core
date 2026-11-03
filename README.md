# NEXUS AI CORE

NEXUS AI CORE is the foundation for a cloud-based, multi-agent system. The current release is an **MVP scaffold**, not a production autonomous agent.

## Current capabilities

- FastAPI service with health, agent registry, task submission and task lookup endpoints.
- Deterministic risk classification and governance approval records.
- Explicit approval gate for sensitive action categories.
- Bearer-token protection for approval decisions.
- GitHub Actions test workflow.

## Important limitations

- Task orchestration is currently a placeholder. No LLM provider or autonomous agent execution is connected yet.
- Storage is in-memory and is lost when the process restarts. PostgreSQL is required before multi-instance or production use.
- The approval endpoint fails closed unless both administrator settings are configured.
- The administrator bearer token is a bootstrap control, not a replacement for a production identity provider, MFA, key rotation, or role-based access control.
- Do not expose this service publicly until authentication, persistent storage, rate limiting, audit durability, and deployment hardening are complete.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest
uvicorn app.main:app --reload
pytest -q
```

## Approval administration

Set these server-side environment variables only in the deployment secret manager:

- `NEXUS_ADMIN_TOKEN`: high-entropy administrator bearer token.
- `NEXUS_ADMIN_ID`: stable identity recorded in the audit trail for the administrator holding that token.

Never commit real credentials to Git. The API does not accept a reviewer identity from the request body.

## API

- `GET /health`
- `GET /agents`
- `POST /tasks`
- `GET /tasks/{task_id}`
- `POST /approvals/{approval_id}/decision` (administrator bearer token required)

## Next engineering milestones

1. Replace in-memory storage with PostgreSQL and durable audit records.
2. Add a provider adapter and connect the first LLM through server-side secrets.
3. Implement bounded agent execution, tool permissions, timeouts and retry policies.
4. Add independent policy enforcement and deployment identity management.
5. Add integration tests and deploy to a low-cost environment only after security gates pass.
