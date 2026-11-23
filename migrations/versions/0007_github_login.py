"""Let a user sign in with GitHub, from several devices

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("github_id", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("github_login", sa.String(100), nullable=True))
    op.create_index("ix_users_github_id", "users", ["github_id"], unique=True)
    op.create_table(
        "user_tokens",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    if op.get_bind().dialect.name == "postgresql":
        # Closed to hosted Data APIs like the other tables (see 0005)
        op.execute("ALTER TABLE user_tokens ENABLE ROW LEVEL SECURITY")


def downgrade():
    op.drop_table("user_tokens")
    op.drop_index("ix_users_github_id", "users")
    op.drop_column("users", "github_login")
    op.drop_column("users", "github_id")
