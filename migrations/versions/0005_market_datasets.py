"""Add immutable historical OHLC datasets.

Revision ID: 0005_market_datasets
Revises: 0004_audit_append_only
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_market_datasets"
down_revision = "0004_audit_append_only"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "market_datasets",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("instrument", sa.String(64), nullable=False),
        sa.Column("timeframe", sa.String(16), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("quality", sa.JSON(), nullable=False),
        sa.Column("candles", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_market_datasets_instrument", "market_datasets", ["instrument"])


def downgrade():
    op.drop_index("ix_market_datasets_instrument", table_name="market_datasets")
    op.drop_table("market_datasets")
