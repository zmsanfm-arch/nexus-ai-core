# NEXUS AI CORE

NEXUS AI CORE is a cloud-oriented multi-agent system under active MVP development.

## Release 0.3.0

- FastAPI central API with authenticated routes and a specification-aware agent registry.
- Static bootstrap bearer auth plus provider-agnostic OIDC JWT verification and group-based roles.
- Central ICT Mentor advisory runtime with schema validation and provenance checks; no execution permissions.
- Provenance-aware source ingestion and lexical retrieval for authorized ICT knowledge segments.
- Strategy specification/experiment registration, immutable strategy versions and evidence-gated lifecycle history.
- Strict OHLC CSV import, immutable dataset storage, deterministic single-position backtest foundation and evaluation metrics.
- SQLAlchemy persistence, Alembic migrations and database-enforced append-only audit triggers.
- GitHub Actions tests and clean-database migration verification.

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
- PostgreSQL: configure `DATABASE_URL`, then apply `alembic upgrade head`.
- Strategy versions and knowledge source IDs are immutable; audit events are append-only under the database migrations.
- SQLite remains a development/single-instance option, not a concurrent multi-instance production database.

## Authentication

For local development, configure distinct `NEXUS_ADMIN_TOKEN` / `NEXUS_ADMIN_ID` and `NEXUS_API_TOKEN` / `NEXUS_API_ID` values. For a hosted deployment, configure `NEXUS_AUTH_MODE=oidc` with issuer, audience, JWKS URL, and admin/operator group mapping. Static tokens are bootstrap-only; never expose them in a browser.

## API

- `GET /health` (public liveness only)
- `GET /agents`, `POST /agents/ict-mentor/invoke`
- `POST /knowledge/sources`, `GET /knowledge/search`
- `POST /market-data/datasets`, dataset metadata/candle reads
- strategy version, experiment and lifecycle routes
- `POST /tasks`, `GET /tasks/{task_id}`
- `POST /approvals/{approval_id}/decision` (admin only)

## Current limitations

- The ICT knowledge search is lexical, not embedding-based RAG; no approved full source corpus has been ingested.
- Backtesting is a deterministic foundation, not a complete portfolio/bid-ask/walk-forward engine.
- PostgreSQL, OIDC provider, web console, MT5 Demo connector, central production Risk Engine and Execution Gateway remain unprovisioned/incomplete.
- Demo promotion and Live trading are disabled. The API is not production-ready; do not expose it publicly.

## Local development

```bash
pip install -r requirements.txt
pip install pytest
uvicorn app.main:app --reload
pytest -q
```

## Architecture specifications

- [Strategy Research & Backtesting](docs/strategy-research/README.md)
- [Strategy lifecycle and promotion gates](docs/strategy-research/STRATEGY_LIFECYCLE.md)
- [NEXUS Web Platform](docs/web-platform/README.md)
- [Dashboard information architecture](docs/web-platform/INFORMATION_ARCHITECTURE.md)
- [Web platform security and access](docs/web-platform/SECURITY_AND_ACCESS.md)
- [Web client API surface](docs/web-platform/API_SURFACE.md)
- [Web platform delivery roadmap](docs/web-platform/DELIVERY_ROADMAP.md)

These documents describe target architecture and proposed contracts. They do not imply that the corresponding web client, backtesting engine, market-data pipeline, Demo connector, or execution services are already deployed.
- [Web platform production-readiness gaps](docs/web-platform/IMPLEMENTATION_GAPS.md)
