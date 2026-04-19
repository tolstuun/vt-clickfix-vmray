"""add enrichment columns

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-19 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("urls", sa.Column("domain", sa.String(255), nullable=True))
    op.add_column("urls", sa.Column("scheme", sa.String(10), nullable=True))
    op.create_index("ix_urls_domain", "urls", ["domain"])

    op.add_column("vmray_submissions", sa.Column("report_url", sa.Text(), nullable=True))
    op.add_column("vmray_submissions", sa.Column("severity", sa.String(50), nullable=True))
    op.add_column("vmray_submissions", sa.Column("submission_status", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("vmray_submissions", "submission_status")
    op.drop_column("vmray_submissions", "severity")
    op.drop_column("vmray_submissions", "report_url")
    op.drop_index("ix_urls_domain", table_name="urls")
    op.drop_column("urls", "scheme")
    op.drop_column("urls", "domain")
