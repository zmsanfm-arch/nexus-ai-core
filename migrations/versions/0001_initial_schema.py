"""Initial NEXUS core and knowledge schema.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_table(
        "approvals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "task_queue",
        sa.Column("task_id", sa.String(length=36), primary_key=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_owner", sa.String(length=128), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_task_queue_status", "task_queue", ["status"])
    op.create_index("ix_task_queue_available_at", "task_queue", ["available_at"])
    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("usage_basis", sa.String(length=32), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(length=160), primary_key=True),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(length=12000), nullable=False),
        sa.Column("timestamp_start", sa.String(length=64), nullable=True),
        sa.Column("timestamp_end", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_knowledge_chunks_source_id", "knowledge_chunks", ["source_id"])


def downgrade():
    op.drop_index("ix_knowledge_chunks_source_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_sources")
    op.drop_index("ix_task_queue_available_at", table_name="task_queue")
    op.drop_index("ix_task_queue_status", table_name="task_queue")
    op.drop_table("task_queue")
    op.drop_table("audit_events")
    op.drop_table("approvals")
    op.drop_table("tasks")
