# NEXUS AI CORE — MVP Scaffold

Version: 0.1.0  
Status: executable foundation scaffold; not production-hardened.

## Requirements
- Docker + Docker Compose, or Python 3.11+
- An OpenAI-compatible model endpoint (optional for the first local API test)

## Run with Docker
1. Copy `.env.example` to `.env`.
2. Run: `docker compose up --build`
3. Open `http://localhost:8000/docs`
4. Health check: `http://localhost:8000/health`

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Initial endpoints
- `GET /health`
- `GET /agents`
- `POST /tasks`
- `GET /tasks/{task_id}`
- `POST /approvals/{approval_id}/decision`

## Security design
- The model/agent layer cannot grant itself permissions.
- Sensitive operations are denied unless an independent approval record exists.
- This scaffold demonstrates policy boundaries; production identity, durable audit storage,
  secret management, network isolation, and cryptographic approval signing remain required.
- Never expose model API keys in prompts, logs, or client-side code.

## Current limitations
This is a starter repository, not a deployed cloud system. No cloud account, DNS, credentials,
or production secrets are included. Do not connect it to real financial accounts or allow
irreversible operations until security review and penetration testing are complete.
