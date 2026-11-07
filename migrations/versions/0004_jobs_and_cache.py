"""Track background indexing and add a result cache

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("repos", sa.Column("status", sa.String(10), nullable=False, server_default="ready"))
    op.add_column("repos", sa.Column("error", sa.Text(), nullable=False, server_default=""))
    op.create_table(
        "cache_entries",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("cache_entries")
    op.drop_column("repos", "error")
    op.drop_column("repos", "status")
