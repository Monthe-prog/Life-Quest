from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        onupdate=now_utc,
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    profile: Mapped["UserProfile"] = relationship(back_populates="user", cascade="all, delete-orphan")
    character: Mapped["CharacterProfile"] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    callsign: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    life_mission: Mapped[Optional[str]] = mapped_column(Text)
    anonymous_on_leaderboard: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="profile")


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class OracleConversation(Base, TimestampMixin):
    __tablename__ = "oracle_conversations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    messages: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class OnboardingAnswer(Base, TimestampMixin):
    __tablename__ = "onboarding_answers"
    __table_args__ = (UniqueConstraint("user_id", "question_key", name="uq_onboarding_user_question"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    question_key: Mapped[str] = mapped_column(String(80), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)


class Goal(Base, TimestampMixin):
    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    horizon: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    part: Mapped[Optional[str]] = mapped_column(String(24))
    target_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    completed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rewarded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class GoalProgress(Base, TimestampMixin):
    __tablename__ = "goal_progress"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    goal_id: Mapped[str] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), index=True, nullable=False)
    delta: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text)


class CalendarBlock(Base, TimestampMixin):
    __tablename__ = "calendar_blocks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    goal_id: Mapped[Optional[str]] = mapped_column(ForeignKey("goals.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    end_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurrence_pattern: Mapped[Optional[str]] = mapped_column(String(80))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    alignment_status: Mapped[str] = mapped_column(String(24), default="unknown", nullable=False)


class WeeklyReview(Base, TimestampMixin):
    __tablename__ = "weekly_reviews"
    __table_args__ = (UniqueConstraint("user_id", "week_ending", name="uq_weekly_review_user_week"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    week_ending: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    wins: Mapped[str] = mapped_column(Text, default="", nullable=False)
    friction: Mapped[str] = mapped_column(Text, default="", nullable=False)
    alignment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    directive: Mapped[str] = mapped_column(Text, default="", nullable=False)
    completion_rate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp_gained: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class WeeklyReviewExport(Base, TimestampMixin):
    __tablename__ = "weekly_review_exports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    review_id: Mapped[Optional[str]] = mapped_column(ForeignKey("weekly_reviews.id", ondelete="SET NULL"))
    filename: Mapped[str] = mapped_column(String(180), nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class CharacterProfile(Base, TimestampMixin):
    __tablename__ = "character_profiles"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    character_class: Mapped[str] = mapped_column(String(40), default="Netrunner", nullable=False)
    head_cosmetic: Mapped[str] = mapped_column(String(40), default="visor", nullable=False)
    body_cosmetic: Mapped[str] = mapped_column(String(40), default="cloak", nullable=False)
    gear_cosmetic: Mapped[str] = mapped_column(String(40), default="blade", nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped[User] = relationship(back_populates="character")


class CharacterStat(Base, TimestampMixin):
    __tablename__ = "character_stats"
    __table_args__ = (UniqueConstraint("user_id", "stat_key", name="uq_character_stat_user_key"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    stat_key: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Achievement(Base, TimestampMixin):
    __tablename__ = "achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_key", name="uq_achievement_user_key"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    achievement_key: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    unlocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class SkillUnlock(Base, TimestampMixin):
    __tablename__ = "skill_unlocks"
    __table_args__ = (UniqueConstraint("user_id", "skill_key", name="uq_skill_user_key"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    skill_key: Mapped[str] = mapped_column(String(80), nullable=False)
    stat_key: Mapped[str] = mapped_column(String(40), nullable=False)
    required_level: Mapped[int] = mapped_column(Integer, nullable=False)
    xp_multiplier: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    streak_multiplier: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    unlocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Quest(Base, TimestampMixin):
    __tablename__ = "quests"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    skill_key: Mapped[Optional[str]] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False)
    reward_xp: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class QuestStep(Base, TimestampMixin):
    __tablename__ = "quest_steps"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    quest_id: Mapped[str] = mapped_column(ForeignKey("quests.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class BossBattle(Base, TimestampMixin):
    __tablename__ = "boss_battles"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    goal_id: Mapped[Optional[str]] = mapped_column(ForeignKey("goals.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    required_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    progress_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reward_xp: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Guild(Base, TimestampMixin):
    __tablename__ = "guilds"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    motto: Mapped[Optional[str]] = mapped_column(String(180))


class GuildMembership(Base, TimestampMixin):
    __tablename__ = "guild_memberships"
    __table_args__ = (UniqueConstraint("guild_id", "user_id", name="uq_guild_member"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    guild_id: Mapped[str] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(24), default="member", nullable=False)


class GuildInviteCode(Base, TimestampMixin):
    __tablename__ = "guild_invite_codes"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    guild_id: Mapped[str] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(6), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class GuildModerationEvent(Base, TimestampMixin):
    __tablename__ = "guild_moderation_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    guild_id: Mapped[str] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"), index=True, nullable=False)
    actor_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    target_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class GuildChatMessage(Base, TimestampMixin):
    __tablename__ = "guild_chat_messages"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    guild_id: Mapped[str] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    goal_id: Mapped[Optional[str]] = mapped_column(ForeignKey("goals.id", ondelete="SET NULL"), index=True)
    task_ref: Mapped[Optional[str]] = mapped_column(String(120))
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hidden_by_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    hidden_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class GuildChatReaction(Base, TimestampMixin):
    __tablename__ = "guild_chat_reactions"
    __table_args__ = (UniqueConstraint("message_id", "user_id", name="uq_guild_chat_reaction_user"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    message_id: Mapped[str] = mapped_column(ForeignKey("guild_chat_messages.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    emoji: Mapped[str] = mapped_column(String(16), nullable=False)


class GuildReactionTrend(Base, TimestampMixin):
    __tablename__ = "guild_reaction_trends"
    __table_args__ = (UniqueConstraint("message_id", name="uq_guild_reaction_trend_message"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    message_id: Mapped[str] = mapped_column(ForeignKey("guild_chat_messages.id", ondelete="CASCADE"), index=True, nullable=False)
    top_emoji: Mapped[Optional[str]] = mapped_column(String(16))
    top_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    previous_top_emoji: Mapped[Optional[str]] = mapped_column(String(16))
    previous_top_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class GuildReactionToggle(Base, TimestampMixin):
    __tablename__ = "guild_reaction_toggles"
    __table_args__ = (UniqueConstraint("message_id", "user_id", name="uq_guild_reaction_toggle_user"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    message_id: Mapped[str] = mapped_column(ForeignKey("guild_chat_messages.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    last_toggled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class ActivityEvent(Base, TimestampMixin):
    __tablename__ = "activity_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    goal_id: Mapped[Optional[str]] = mapped_column(ForeignKey("goals.id", ondelete="SET NULL"))
    event_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
