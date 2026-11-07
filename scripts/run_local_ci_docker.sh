#!/usr/bin/env bash
# Run NEXUS local CI using Docker only; no GitHub Actions minutes are consumed.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CI_IMAGE="${NEXUS_CI_IMAGE:-nexus-ai-core-ci:local}"
APP_IMAGE="${NEXUS_APP_IMAGE:-nexus-ai-core:ci}"
NETWORK="nexus-local-ci-${RANDOM}-$$"
PG_NAME="nexus-local-ci-postgres-${RANDOM}-$$"
APP_NAME="nexus-local-ci-app-${RANDOM}-$$"
PG_USER="${NEXUS_CI_PG_USER:-postgres}"
PG_PASSWORD="${NEXUS_CI_PG_PASSWORD:-postgres}"
PG_DATABASE="${NEXUS_CI_PG_DATABASE:-nexus_test}"
APP_PORT="${NEXUS_CI_APP_PORT:-18080}"

cleanup() {
  docker rm -f "$APP_NAME" "$PG_NAME" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
}
trap cleanup EXIT

command -v docker >/dev/null 2>&1 || {
  echo "ERROR: Docker CLI is not installed or not in PATH." >&2
  exit 127
}
docker info >/dev/null 2>&1 || {
  echo "ERROR: Docker daemon is not running or this user cannot access it." >&2
  exit 1
}

for required in requirements.txt requirements-browser.txt Dockerfile; do
  [[ -f "$ROOT/$required" ]] || {
    echo "ERROR: Missing repository file: $required" >&2
    exit 2
  }
done
[[ -f "$ROOT/Dockerfile.ci" ]] || {
  echo "ERROR: Dockerfile.ci is missing. Keep it at the repository root." >&2
  exit 2
}

echo "==> Create isolated Docker network"
docker network create "$NETWORK" >/dev/null

echo "==> Start disposable PostgreSQL 16 test database"
docker run -d \
  --name "$PG_NAME" \
  --network "$NETWORK" \
  --network-alias nexus-postgres \
  -e POSTGRES_USER="$PG_USER" \
  -e POSTGRES_PASSWORD="$PG_PASSWORD" \
  -e POSTGRES_DB="$PG_DATABASE" \
  --health-cmd="pg_isready -U $PG_USER -d $PG_DATABASE" \
  --health-interval=3s \
  --health-timeout=3s \
  --health-retries=30 \
  postgres:16 >/dev/null

for attempt in $(seq 1 60); do
  state="$(docker inspect --format='{{.State.Health.Status}}' "$PG_NAME")"
  [[ "$state" == "healthy" ]] && break
  [[ "$state" == "unhealthy" ]] && {
    docker logs "$PG_NAME"
    echo "ERROR: PostgreSQL failed its health check." >&2
    exit 1
  }
  sleep 2
done
[[ "$(docker inspect --format='{{.State.Health.Status}}' "$PG_NAME")" == "healthy" ]] || {
  docker logs "$PG_NAME"
  echo "ERROR: PostgreSQL did not become healthy in time." >&2
  exit 1
}

echo "==> Build local test/security/browser image"
docker build -f "$ROOT/Dockerfile.ci" -t "$CI_IMAGE" "$ROOT"

echo "==> Run pytest, dependency audit, Bandit and Playwright browser tests"
docker run --rm \
  --network "$NETWORK" \
  -e NEXUS_TEST_POSTGRES_URL="postgresql+psycopg://$PG_USER:$PG_PASSWORD@nexus-postgres:5432/$PG_DATABASE" \
  -e NEXUS_BROWSER_ARTIFACT_DIR=/workspace/artifacts/browser-test \
  -v "$ROOT:/workspace" \
  -w /workspace \
  "$CI_IMAGE" \
  bash -Eeuo pipefail -c '
    echo "--- pytest ---"
    pytest -q
    echo "--- pip-audit ---"
    pip-audit -r requirements.txt
    echo "--- Bandit ---"
    bandit -r app scripts -ll
    echo "--- Playwright browser fixture ---"
    pytest -q tests/test_browser_test.py
  '

echo "==> Build production application image"
docker build -t "$APP_IMAGE" "$ROOT"

echo "==> Smoke-test application container"
docker run -d \
  --name "$APP_NAME" \
  --network "$NETWORK" \
  -p "127.0.0.1:$APP_PORT:8000" \
  "$APP_IMAGE" >/dev/null

for attempt in $(seq 1 40); do
  state="$(docker inspect --format='{{.State.Health.Status}}' "$APP_NAME" 2>/dev/null || true)"
  [[ "$state" == "healthy" ]] && {
    echo "SUCCESS: pytest, security checks, browser tests, Docker build and container health passed."
    exit 0
  }
  [[ "$state" == "unhealthy" ]] && {
    docker logs "$APP_NAME"
    echo "ERROR: Application container became unhealthy." >&2
    exit 1
  }
  sleep 2
done

docker logs "$APP_NAME"
echo "ERROR: Application container did not become healthy in time." >&2
exit 1
