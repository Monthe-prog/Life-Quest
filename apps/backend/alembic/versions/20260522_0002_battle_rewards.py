"""battle rewards

Revision ID: 20260522_0002
Revises: 20260522_0001
Create Date: 2026-05-22
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260522_0002"
down_revision: str | None = "20260522_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("goals", sa.Column("rewarded_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "activity_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("goal_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("goals.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_activity_events_user_id"), "activity_events", ["user_id"])
    op.create_index(op.f("ix_activity_events_event_type"), "activity_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("activity_events")
    op.drop_column("goals", "rewarded_at")
