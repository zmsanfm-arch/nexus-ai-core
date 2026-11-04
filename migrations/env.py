import os
from logging.config import fileConfig

# Importing app.storage creates the module-level application store. Disable its
# automatic migration side effect while Alembic imports model metadata; the
# explicit migration command owns the connection and migration transaction.
os.environ["NEXUS_MIGRATION_COMMAND"] = "true"

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from app.storage import Base
from app.services.knowledge_store import metadata as knowledge_metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = [Base.metadata, knowledge_metadata]


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    # Serialize concurrent PostgreSQL migration jobs across app instances.
    # The transaction-scoped lock is released automatically on commit/rollback.
    if connection.dialect.name == "postgresql":
        connection.execute(text("SELECT pg_advisory_xact_lock(731946205118)"))
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    supplied_connection = config.attributes.get("connection")
    if supplied_connection is not None:
        do_run_migrations(supplied_connection)
        return
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
