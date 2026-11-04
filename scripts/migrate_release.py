"""Run the production PostgreSQL schema migration as a one-shot release step.

This entrypoint is deliberately separate from API startup. It disables the
module-level store's implicit migration before importing app.storage, requires
a PostgreSQL DATABASE_URL, then runs the Alembic head migration explicitly.
"""
from __future__ import annotations

import os
from sqlalchemy.engine import make_url


def main() -> None:
    # Importing app.storage creates the module-level application store. Keep
    # that side effect migration-free; this script owns the one-shot migration.
    os.environ["NEXUS_MIGRATION_COMMAND"] = "true"
    os.environ["NEXUS_SKIP_MIGRATIONS"] = "false"

    raw_url = os.environ.get("DATABASE_URL")
    if not raw_url:
        raise RuntimeError("DATABASE_URL is required for the production migration release job.")

    url = make_url(raw_url)
    if url.get_backend_name() != "postgresql":
        raise RuntimeError("Production schema migrations require PostgreSQL; refusing a non-PostgreSQL target.")

    # Do not print the URL or credentials. The target metadata is safe to log.
    print(
        "NEXUS migration target:",
        url.get_backend_name(),
        url.host,
        url.database,
        flush=True,
    )

    from app.storage import SQLAlchemyStore

    store = SQLAlchemyStore(database_url=raw_url, run_migrations=True)
    try:
        store.check_database()
    finally:
        store.close()


if __name__ == "__main__":
    main()
