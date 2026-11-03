"""Add provenance-aware knowledge sources and chunks.

Revision ID: 0003_knowledge_sources
Revises: 0002_research_demo_records
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_knowledge_sources"
down_revision = "0002_research_demo_records"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("usage_basis", sa.String(32), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(12000), nullable=False),
        sa.Column("timestamp_start", sa.String(64), nullable=True),
        sa.Column("timestamp_end", sa.String(64), nullable=True),
    )
    op.create_index("ix_knowledge_chunks_source_id", "knowledge_chunks", ["source_id"])


def downgrade():
    op.drop_index("ix_knowledge_chunks_source_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_sources")
