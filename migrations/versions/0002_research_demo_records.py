"""Add immutable strategy versions and typed research/demo records.

Revision ID: 0002_research_demo_records
Revises: 0001_initial_core
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_research_demo_records"
down_revision = "0001_initial_core"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "strategy_versions",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("strategy_id", sa.String(64), nullable=False, index=True),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("strategy_id", "version", name="uq_strategy_version"),
    )
    op.create_table(
        "research_records",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("record_type", sa.String(32), nullable=False, index=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "trading_records",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("record_type", sa.String(32), nullable=False, index=True),
        sa.Column("environment", sa.String(16), nullable=False, index=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("trading_records")
    op.drop_table("research_records")
    op.drop_table("strategy_versions")
