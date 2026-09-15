"""widen tender deadline and date columns to varchar 255

Fixes a production bug on Render: tenders.issue_date, .submission_deadline,
and .delivery_deadline were VARCHAR(32). These are LLM-extracted free-text
phrases from tender prose (e.g. "12 months from date of contract signing" —
39 characters), not normalized dates, and have no real fixed maximum length.
A real tender's delivery_deadline exceeded 32 characters and Postgres raised
StringDataRightTruncation on the UPDATE, which (via a separate exception-
handling bug, fixed alongside this migration) then cascaded into a second,
more confusing failure.

Safe to run against the existing Render database as-is: this only widens
already-nullable VARCHAR columns (a metadata-only change in Postgres, no
table rewrite, no data loss) — every previously-stored value already fits
inside the new length, since it fit inside the old one.

Revision ID: 4de9c48359be
Revises:
Create Date: 2026-09-16 03:40:19.856328

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4de9c48359be'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("tenders") as batch_op:
        batch_op.alter_column(
            "issue_date", existing_type=sa.String(length=32), type_=sa.String(length=255), existing_nullable=True,
        )
        batch_op.alter_column(
            "submission_deadline", existing_type=sa.String(length=32), type_=sa.String(length=255), existing_nullable=True,
        )
        batch_op.alter_column(
            "delivery_deadline", existing_type=sa.String(length=32), type_=sa.String(length=255), existing_nullable=True,
        )


def downgrade() -> None:
    # NOTE: this direction can fail (or silently truncate on some backends)
    # if any row has since acquired a value longer than 32 characters — which
    # is exactly the situation this migration exists to allow. Only run this
    # downgrade if you've confirmed no such rows exist.
    with op.batch_alter_table("tenders") as batch_op:
        batch_op.alter_column(
            "delivery_deadline", existing_type=sa.String(length=255), type_=sa.String(length=32), existing_nullable=True,
        )
        batch_op.alter_column(
            "submission_deadline", existing_type=sa.String(length=255), type_=sa.String(length=32), existing_nullable=True,
        )
        batch_op.alter_column(
            "issue_date", existing_type=sa.String(length=255), type_=sa.String(length=32), existing_nullable=True,
        )
