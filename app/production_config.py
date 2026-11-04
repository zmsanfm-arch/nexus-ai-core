from __future__ import annotations

import os
from collections.abc import Mapping


_TRUE_VALUES = {"1", "true", "yes"}


def validate_production_environment(environ: Mapping[str, str] | None = None) -> list[str]:
    """Return safe configuration errors without ever echoing secret values."""
    values = os.environ if environ is None else environ
    if values.get("APP_ENV", "").strip().lower() != "production":
        return []

    errors: list[str] = []
    required = (
        "DATABASE_URL",
        "NEXUS_API_TOKEN",
        "NEXUS_API_CLIENT_ID",
        "NEXUS_ADMIN_TOKEN",
        "NEXUS_ADMIN_ID",
    )
    for key in required:
        if not values.get(key, "").strip():
            errors.append(f"{key} is required")

    secrets = {}
    for key in ("NEXUS_API_TOKEN", "NEXUS_ADMIN_TOKEN"):
        value = values.get(key, "")
        if value:
            if len(value) < 32:
                errors.append(f"{key} must contain at least 32 characters")
            if any(marker in value.lower() for marker in ("replace_with", "changeme", "example")):
                errors.append(f"{key} still contains a placeholder value")
            if any(char.isspace() for char in value):
                errors.append(f"{key} must not contain whitespace")
            secrets[key] = value

    if len(secrets) == 2 and secrets["NEXUS_API_TOKEN"] == secrets["NEXUS_ADMIN_TOKEN"]:
        errors.append("NEXUS_API_TOKEN and NEXUS_ADMIN_TOKEN must be different")

    database_url = values.get("DATABASE_URL", "").strip().lower()
    if database_url and not database_url.startswith(("postgresql://", "postgresql+psycopg://")):
        errors.append("production DATABASE_URL must use PostgreSQL")

    for key, default in (("NEXUS_API_RATE_LIMIT_PER_MINUTE", 600), ("NEXUS_ADMIN_RATE_LIMIT_PER_MINUTE", 300)):
        raw_limit = values.get(key, str(default)).strip()
        try:
            limit = int(raw_limit)
        except ValueError:
            errors.append(f"{key} must be an integer")
            continue
        if limit < 1 or limit > 100000:
            errors.append(f"{key} must be between 1 and 100000")

    skip_migrations = values.get("NEXUS_SKIP_MIGRATIONS", "").strip().lower()
    if skip_migrations not in _TRUE_VALUES:
        errors.append("production API must use the dedicated migration release job")

    return errors
