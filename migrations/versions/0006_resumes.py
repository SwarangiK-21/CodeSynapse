"""Let a job description record be a resume, whose requirements are the person's claims

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("job_descriptions", sa.Column("kind", sa.String(10), nullable=False, server_default="job"))


def downgrade():
    op.drop_column("job_descriptions", "kind")
