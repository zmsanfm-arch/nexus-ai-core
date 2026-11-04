"""Indexed lexical terms for scalable cross-database knowledge retrieval.

Revision ID: 0002_knowledge_terms
Revises: 0001_initial
"""
import re
import unicodedata

from alembic import op
import sqlalchemy as sa

revision = "0002_knowledge_terms"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _tokens(value):
    value = unicodedata.normalize("NFKC", value).translate(str.maketrans({
        "ي": "ی", "ى": "ی", "ك": "ک", "ـ": "",
    }))
    value = "".join(
        char for char in value
        if unicodedata.category(char) not in {"Mn", "Me", "Cf"}
    ).casefold()
    return set(re.findall(r"[^\\W_]{2,}", value, flags=re.UNICODE))


def upgrade():
    op.create_table(
        "knowledge_chunk_terms",
        sa.Column("chunk_id", sa.String(length=160), nullable=False),
        sa.Column("term", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("chunk_id", "term", name="pk_knowledge_chunk_terms"),
    )
    op.create_index(
        "ix_knowledge_chunk_terms_term",
        "knowledge_chunk_terms", ["term"],
    )
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, text FROM knowledge_chunks")).mappings()
    batch = []
    for row in rows:
        for term in _tokens(row["text"]):
            if len(term) <= 128:
                batch.append({"chunk_id": row["id"], "term": term})
        if len(batch) >= 1000:
            connection.execute(
                sa.text("INSERT INTO knowledge_chunk_terms (chunk_id, term) VALUES (:chunk_id, :term)"),
                batch,
            )
            batch.clear()
    if batch:
        connection.execute(
            sa.text("INSERT INTO knowledge_chunk_terms (chunk_id, term) VALUES (:chunk_id, :term)"),
            batch,
        )


def downgrade():
    op.drop_index("ix_knowledge_chunk_terms_term", table_name="knowledge_chunk_terms")
    op.drop_table("knowledge_chunk_terms")
