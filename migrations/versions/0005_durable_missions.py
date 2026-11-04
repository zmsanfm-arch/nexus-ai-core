"""Durable mission runs, node checkpoints, and dedicated queue.

Revision ID: 0005_durable_missions
Revises: 0004_missions
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_durable_missions"
down_revision = "0004_missions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mission_runs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("mission_id", sa.String(64), nullable=False, index=True),
        sa.Column("principal_id", sa.String(128), nullable=False, index=True),
        sa.Column("status", sa.String(24), nullable=False, index=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("mission_id", "principal_id", "idempotency_key", name="uq_mission_run_idempotency"),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
    )
    op.create_table(
        "mission_node_runs",
        sa.Column("run_id", sa.String(64), primary_key=True),
        sa.Column("node_id", sa.String(64), primary_key=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "mission_queue",
        sa.Column("run_id", sa.String(64), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False, index=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("lease_owner", sa.String(128), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("mission_queue")
    op.drop_table("mission_node_runs")
    op.drop_table("mission_runs")
