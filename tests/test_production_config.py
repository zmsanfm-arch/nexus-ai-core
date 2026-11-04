from app.production_config import validate_production_environment


def valid_environment():
    return {
        "APP_ENV": "production",
        "DATABASE_URL": "postgresql+psycopg://nexus:secret@postgres:5432/nexus",
        "NEXUS_API_TOKEN": "a" * 48,
        "NEXUS_API_CLIENT_ID": "production-api",
        "NEXUS_ADMIN_TOKEN": "b" * 48,
        "NEXUS_ADMIN_ID": "production-admin",
        "NEXUS_SKIP_MIGRATIONS": "true",
    }


def test_valid_production_environment_passes():
    assert validate_production_environment(valid_environment()) == []


def test_nonproduction_environment_is_not_subject_to_production_preflight():
    assert validate_production_environment({"APP_ENV": "development"}) == []


def test_production_rejects_missing_or_weak_secrets():
    env = valid_environment()
    env["NEXUS_API_TOKEN"] = "short"
    env["NEXUS_ADMIN_TOKEN"] = ""
    errors = validate_production_environment(env)
    assert any("NEXUS_API_TOKEN" in item for item in errors)
    assert any("NEXUS_ADMIN_TOKEN" in item for item in errors)


def test_production_rejects_placeholder_and_reused_tokens():
    env = valid_environment()
    env["NEXUS_API_TOKEN"] = "REPLACE_WITH_A_LONG_RANDOM_SECRET_VALUE"
    env["NEXUS_ADMIN_TOKEN"] = env["NEXUS_API_TOKEN"]
    errors = validate_production_environment(env)
    assert any("placeholder" in item for item in errors)
    assert any("must be different" in item for item in errors)


def test_production_requires_postgres_and_dedicated_migrations():
    env = valid_environment()
    env["DATABASE_URL"] = "sqlite:///./nexus.db"
    env["NEXUS_SKIP_MIGRATIONS"] = "false"
    errors = validate_production_environment(env)
    assert any("PostgreSQL" in item for item in errors)
    assert any("migration release job" in item for item in errors)


def test_validation_errors_never_include_secret_values():
    env = valid_environment()
    env["NEXUS_API_TOKEN"] = "top-secret-placeholder"
    errors = validate_production_environment(env)
    assert "top-secret-placeholder" not in " ".join(errors)


def test_production_rate_limits_must_be_positive_bounded_integers():
    env = valid_environment()
    env["NEXUS_API_RATE_LIMIT_PER_MINUTE"] = "0"
    env["NEXUS_ADMIN_RATE_LIMIT_PER_MINUTE"] = "not-a-number"
    errors = validate_production_environment(env)
    assert any("NEXUS_API_RATE_LIMIT_PER_MINUTE" in item for item in errors)
    assert any("NEXUS_ADMIN_RATE_LIMIT_PER_MINUTE" in item for item in errors)


def test_production_rate_limits_accept_configured_positive_values():
    env = valid_environment()
    env["NEXUS_API_RATE_LIMIT_PER_MINUTE"] = "1200"
    env["NEXUS_ADMIN_RATE_LIMIT_PER_MINUTE"] = "600"
    assert validate_production_environment(env) == []
