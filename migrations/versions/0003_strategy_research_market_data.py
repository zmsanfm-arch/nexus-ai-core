"""Add immutable strategy research and historical market datasets.

Revision ID: 0003_strategy_research_market_data
Revises: 0002_knowledge_terms
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_strategy_research_market_data"
down_revision = "0002_knowledge_terms"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "strategy_versions",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("strategy_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_strategy_versions_strategy_id", "strategy_versions", ["strategy_id"])
    op.create_table(
        "research_records",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("record_type", sa.String(length=32), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_research_records_record_type", "research_records", ["record_type"])
    op.create_table(
        "market_datasets",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("instrument", sa.String(length=64), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("quality", sa.JSON(), nullable=False),
        sa.Column("candles", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_market_datasets_instrument", "market_datasets", ["instrument"])


def downgrade():
    op.drop_index("ix_market_datasets_instrument", table_name="market_datasets")
    op.drop_table("market_datasets")
    op.drop_index("ix_research_records_record_type", table_name="research_records")
    op.drop_table("research_records")
    op.drop_index("ix_strategy_versions_strategy_id", table_name="strategy_versions")
    op.drop_table("strategy_versions")
