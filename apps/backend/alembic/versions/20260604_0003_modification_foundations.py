"""add modification foundation tables

Revision ID: 20260604_0003
Revises: 20260522_0002
Create Date: 2026-06-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260604_0003"
down_revision = "20260522_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("vision_3_5_year", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("one_year_goal", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("calendar_blocks", sa.Column("is_recurring", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("calendar_blocks", sa.Column("recurrence_pattern", sa.String(length=80), nullable=True))
    op.add_column("calendar_blocks", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("calendar_blocks", sa.Column("alignment_status", sa.String(length=24), nullable=False, server_default="unknown"))

    op.add_column("skill_unlocks", sa.Column("xp_multiplier", sa.Integer(), nullable=False, server_default="100"))
    op.add_column("skill_unlocks", sa.Column("streak_multiplier", sa.Integer(), nullable=False, server_default="100"))
    op.add_column("skill_unlocks", sa.Column("description", sa.Text(), nullable=True))

    op.create_table(
        "weekly_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("week_ending", sa.Date(), nullable=False),
        sa.Column("wins", sa.Text(), nullable=False, server_default=""),
        sa.Column("friction", sa.Text(), nullable=False, server_default=""),
        sa.Column("alignment", sa.Text(), nullable=False, server_default=""),
        sa.Column("directive", sa.Text(), nullable=False, server_default=""),
        sa.Column("completion_rate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("xp_gained", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "week_ending", name="uq_weekly_review_user_week"),
    )
    op.create_index(op.f("ix_weekly_reviews_user_id"), "weekly_reviews", ["user_id"])
    op.create_index(op.f("ix_weekly_reviews_week_ending"), "weekly_reviews", ["week_ending"])

    op.create_table(
        "weekly_review_exports",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("review_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("filename", sa.String(length=180), nullable=False),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["review_id"], ["weekly_reviews.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_weekly_review_exports_user_id"), "weekly_review_exports", ["user_id"])

    op.create_table(
        "quests",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("skill_key", sa.String(length=80), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("reward_xp", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quests_user_id"), "quests", ["user_id"])

    op.create_table(
        "boss_battles",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("goal_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("required_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("progress_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reward_xp", sa.Integer(), nullable=False, server_default="500"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_boss_battles_user_id"), "boss_battles", ["user_id"])

    op.create_table(
        "quest_steps",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("quest_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["quest_id"], ["quests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quest_steps_quest_id"), "quest_steps", ["quest_id"])

    op.create_table(
        "guild_chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("guild_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("goal_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hidden_by_user_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("top_emoji", sa.String(length=16), nullable=True),
        sa.Column("top_emoji_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("previous_top_emoji", sa.String(length=16), nullable=True),
        sa.Column("previous_top_emoji_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trend_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["hidden_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_guild_chat_messages_guild_id"), "guild_chat_messages", ["guild_id"])
    op.create_index(op.f("ix_guild_chat_messages_user_id"), "guild_chat_messages", ["user_id"])

    op.create_table(
        "guild_chat_reactions",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("emoji", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["guild_chat_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "user_id", name="uq_guild_message_user_reaction"),
    )
    op.create_index(op.f("ix_guild_chat_reactions_message_id"), "guild_chat_reactions", ["message_id"])
    op.create_index(op.f("ix_guild_chat_reactions_user_id"), "guild_chat_reactions", ["user_id"])

    op.create_table(
        "guild_moderation_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("guild_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_guild_moderation_events_actor_user_id"), "guild_moderation_events", ["actor_user_id"])
    op.create_index(op.f("ix_guild_moderation_events_guild_id"), "guild_moderation_events", ["guild_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_guild_moderation_events_guild_id"), table_name="guild_moderation_events")
    op.drop_index(op.f("ix_guild_moderation_events_actor_user_id"), table_name="guild_moderation_events")
    op.drop_table("guild_moderation_events")
    op.drop_index(op.f("ix_guild_chat_reactions_user_id"), table_name="guild_chat_reactions")
    op.drop_index(op.f("ix_guild_chat_reactions_message_id"), table_name="guild_chat_reactions")
    op.drop_table("guild_chat_reactions")
    op.drop_index(op.f("ix_guild_chat_messages_user_id"), table_name="guild_chat_messages")
    op.drop_index(op.f("ix_guild_chat_messages_guild_id"), table_name="guild_chat_messages")
    op.drop_table("guild_chat_messages")
    op.drop_index(op.f("ix_quest_steps_quest_id"), table_name="quest_steps")
    op.drop_table("quest_steps")
    op.drop_index(op.f("ix_boss_battles_user_id"), table_name="boss_battles")
    op.drop_table("boss_battles")
    op.drop_index(op.f("ix_quests_user_id"), table_name="quests")
    op.drop_table("quests")
    op.drop_index(op.f("ix_weekly_review_exports_user_id"), table_name="weekly_review_exports")
    op.drop_table("weekly_review_exports")
    op.drop_index(op.f("ix_weekly_reviews_week_ending"), table_name="weekly_reviews")
    op.drop_index(op.f("ix_weekly_reviews_user_id"), table_name="weekly_reviews")
    op.drop_table("weekly_reviews")

    op.drop_column("skill_unlocks", "description")
    op.drop_column("skill_unlocks", "streak_multiplier")
    op.drop_column("skill_unlocks", "xp_multiplier")

    op.drop_column("calendar_blocks", "alignment_status")
    op.drop_column("calendar_blocks", "completed_at")
    op.drop_column("calendar_blocks", "recurrence_pattern")
    op.drop_column("calendar_blocks", "is_recurring")

    op.drop_column("user_profiles", "onboarding_completed_at")
    op.drop_column("user_profiles", "one_year_goal")
    op.drop_column("user_profiles", "vision_3_5_year")
