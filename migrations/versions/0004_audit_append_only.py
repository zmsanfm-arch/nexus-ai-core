"""Enforce append-only audit events at the database layer.

Revision ID: 0004_audit_append_only
Revises: 0003_knowledge_sources
"""
from alembic import op

revision = "0004_audit_append_only"
down_revision = "0003_knowledge_sources"
branch_labels = None
depends_on = None


def upgrade():
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute("""
            CREATE TRIGGER audit_events_no_update
            BEFORE UPDATE ON audit_events
            BEGIN SELECT RAISE(ABORT, 'audit_events are append-only'); END;
        """)
        op.execute("""
            CREATE TRIGGER audit_events_no_delete
            BEFORE DELETE ON audit_events
            BEGIN SELECT RAISE(ABORT, 'audit_events are append-only'); END;
        """)
    elif dialect == "postgresql":
        op.execute("""
            CREATE FUNCTION reject_audit_mutation() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'audit_events are append-only';
            END;
            $$ LANGUAGE plpgsql;
        """)
        op.execute("""
            CREATE TRIGGER audit_events_no_mutation
            BEFORE UPDATE OR DELETE ON audit_events
            FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation();
        """)


def downgrade():
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS audit_events_no_update")
        op.execute("DROP TRIGGER IF EXISTS audit_events_no_delete")
    elif dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS audit_events_no_mutation ON audit_events")
        op.execute("DROP FUNCTION IF EXISTS reject_audit_mutation()")
