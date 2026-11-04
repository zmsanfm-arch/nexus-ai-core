"""Persist user-owned mission definitions.

Revision ID: 0004_missions
Revises: 0003_research_market_data
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_missions"
down_revision = "0003_research_market_data"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "missions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("principal_id", sa.String(length=128), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_missions_principal_id", "missions", ["principal_id"])


def downgrade():
    op.drop_index("ix_missions_principal_id", table_name="missions")
    op.drop_table("missions")
