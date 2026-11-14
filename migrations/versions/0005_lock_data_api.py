"""Turn on row-level security so hosted Postgres APIs can't read the tables

Supabase publishes every table in the public schema through its Data API. With row-level
security on and no policies, that API can read nothing. The app connects as the table owner,
which row-level security doesn't apply to, so it is unaffected.

Revision ID: 0005
Revises: 0004
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

TABLES = ["alembic_version", "users", "profiles", "chat_messages", "repos", "code_chunks",
          "job_descriptions", "analyses", "cache_entries"]


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
