"""guild social

Revision ID: 20260606_0003
Revises: 20260604_0003
Create Date: 2026-06-06
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "20260606_0003"
down_revision: str | None = "20260604_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def table_exists(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def column_exists(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def index_exists(table_name: str, index_name: str) -> bool:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return False
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    if not index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    if not column_exists("user_profiles", "anonymous_on_leaderboard"):
        op.add_column(
            "user_profiles",
            sa.Column("anonymous_on_leaderboard", sa.Boolean(), server_default=sa.false(), nullable=False),
        )

    if not table_exists("guild_moderation_events"):
        op.create_table(
            "guild_moderation_events",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            sa.Column("guild_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False),
            sa.Column("actor_user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("target_user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("event_type", sa.String(length=40), nullable=False),
            sa.Column("payload", postgresql.JSONB(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    create_index_if_missing(op.f("ix_guild_moderation_events_guild_id"), "guild_moderation_events", ["guild_id"])
    create_index_if_missing(op.f("ix_guild_moderation_events_actor_user_id"), "guild_moderation_events", ["actor_user_id"])
    create_index_if_missing(op.f("ix_guild_moderation_events_target_user_id"), "guild_moderation_events", ["target_user_id"])

    if not table_exists("guild_chat_messages"):
        op.create_table(
            "guild_chat_messages",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            sa.Column("guild_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("goal_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("goals.id", ondelete="SET NULL")),
            sa.Column("task_ref", sa.String(length=120)),
            sa.Column("is_hidden", sa.Boolean(), nullable=False),
            sa.Column("hidden_by_user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("hidden_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    create_index_if_missing(op.f("ix_guild_chat_messages_guild_id"), "guild_chat_messages", ["guild_id"])
    create_index_if_missing(op.f("ix_guild_chat_messages_user_id"), "guild_chat_messages", ["user_id"])
    create_index_if_missing(op.f("ix_guild_chat_messages_goal_id"), "guild_chat_messages", ["goal_id"])

    if not table_exists("guild_chat_reactions"):
        op.create_table(
            "guild_chat_reactions",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            sa.Column("message_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("guild_chat_messages.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("emoji", sa.String(length=16), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("message_id", "user_id", name="uq_guild_chat_reaction_user"),
        )
    create_index_if_missing(op.f("ix_guild_chat_reactions_message_id"), "guild_chat_reactions", ["message_id"])
    create_index_if_missing(op.f("ix_guild_chat_reactions_user_id"), "guild_chat_reactions", ["user_id"])

    if not table_exists("guild_reaction_trends"):
        op.create_table(
            "guild_reaction_trends",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            sa.Column("message_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("guild_chat_messages.id", ondelete="CASCADE"), nullable=False),
            sa.Column("top_emoji", sa.String(length=16)),
            sa.Column("top_count", sa.Integer(), nullable=False),
            sa.Column("previous_top_emoji", sa.String(length=16)),
            sa.Column("previous_top_count", sa.Integer(), nullable=False),
            sa.Column("last_changed_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("message_id", name="uq_guild_reaction_trend_message"),
        )
    create_index_if_missing(op.f("ix_guild_reaction_trends_message_id"), "guild_reaction_trends", ["message_id"])

    if not table_exists("guild_reaction_toggles"):
        op.create_table(
            "guild_reaction_toggles",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            sa.Column("message_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("guild_chat_messages.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("last_toggled_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("message_id", "user_id", name="uq_guild_reaction_toggle_user"),
        )
    create_index_if_missing(op.f("ix_guild_reaction_toggles_message_id"), "guild_reaction_toggles", ["message_id"])
    create_index_if_missing(op.f("ix_guild_reaction_toggles_user_id"), "guild_reaction_toggles", ["user_id"])


def downgrade() -> None:
    op.drop_table("guild_reaction_toggles")
    op.drop_table("guild_reaction_trends")
    op.drop_table("guild_chat_reactions")
    op.drop_table("guild_chat_messages")
    op.drop_table("guild_moderation_events")
    op.drop_column("user_profiles", "anonymous_on_leaderboard")
