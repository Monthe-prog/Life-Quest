from __future__ import annotations

import random
import string
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import (
    ActivityEvent,
    CharacterProfile,
    CharacterStat,
    Goal,
    Guild,
    GuildChatMessage,
    GuildChatReaction,
    GuildInviteCode,
    GuildMembership,
    GuildModerationEvent,
    GuildReactionToggle,
    GuildReactionTrend,
    User,
    UserProfile,
    now_utc,
)

router = APIRouter()

GUILD_MAX_MEMBERS = 10
GUILD_MAX_MODERATORS = 2
REACTION_RATE_LIMIT_SECONDS = 2
QUICK_EMOJI = ["🔥", "💪", "✅", "🎯", "🙌", "🧠"]


class GuildForgeRequest(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    motto: str | None = Field(default=None, max_length=180)


class GuildJoinRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized.isalnum():
            raise ValueError("Code must be alphanumeric")
        return normalized


class GuildMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=1000)
    goal_id: str | None = None
    task_ref: str | None = Field(default=None, max_length=120)


class GuildReactionRequest(BaseModel):
    emoji: str = Field(min_length=1, max_length=16)

    @field_validator("emoji")
    @classmethod
    def supported_emoji(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in QUICK_EMOJI:
            raise ValueError("Unsupported reaction")
        return normalized


class GuildRoleRequest(BaseModel):
    role: Literal["moderator", "member"]


class LeaderboardPrivacyRequest(BaseModel):
    anonymous_on_leaderboard: bool


class GuildResponse(BaseModel):
    id: str
    name: str
    motto: str | None
    role: str | None = None
    invite_code: str | None = None
    member_count: int = 0
    guild_xp: int = 0


class GuildStatusResponse(BaseModel):
    aligned: bool
    guild: GuildResponse | None


class GuildMemberResponse(BaseModel):
    user_id: str
    callsign: str
    role: str
    xp: int
    level: int
    completion_rate: float
    anonymous_on_leaderboard: bool
    is_current_user: bool = False
    joined_at: str


class LeaderboardEntryResponse(BaseModel):
    user_id: str
    display_name: str
    rank: int
    xp: int
    weekly_xp: int
    streak_length: int
    stat_key: str | None = None
    stat_xp: int | None = None


class ModerationEventResponse(BaseModel):
    id: str
    event_type: str
    actor: str
    target: str | None
    created_at: str
    detail: str | None = None


class ReactionTrendResponse(BaseModel):
    top_emoji: str | None
    top_count: int
    previous_top_emoji: str | None
    previous_top_count: int
    last_changed_at: str | None


class GuildMessageResponse(BaseModel):
    id: str
    author_id: str
    author: str
    body: str
    goal_id: str | None
    task_ref: str | None
    created_at: str
    reactions: dict[str, int]
    my_reaction: str | None
    suggested_emoji: str
    trend: ReactionTrendResponse


class GuildOverviewResponse(BaseModel):
    guild: GuildResponse
    members: list[GuildMemberResponse]
    leaderboard: list[LeaderboardEntryResponse]
    moderation_feed: list[ModerationEventResponse]


class FeedEventResponse(BaseModel):
    id: str
    event_type: str
    operator: str
    goal_title: str | None
    xp_awarded: int | None
    stat_key: str | None
    created_at: str


class GuildMemberResponse(BaseModel):
    user_id: str
    operator: str
    role: str


class GuildLeaderboardEntry(BaseModel):
    guild_id: str
    name: str
    member_xp_sum: int
    guild_xp: int


class GuildChatCreate(BaseModel):
    body: str = Field(min_length=1, max_length=1000)
    goal_id: str | None = None


class GuildChatResponse(BaseModel):
    id: str
    body: str
    operator: str
    user_id: str
    goal_id: str | None
    hidden: bool
    reaction_counts: dict[str, int]
    top_emoji: str | None
    top_emoji_count: int
    previous_top_emoji: str | None
    previous_top_emoji_count: int
    trend_changed_at: str | None
    created_at: str


class ReactionPayload(BaseModel):
    emoji: str = Field(min_length=1, max_length=16)


class ModerationEventResponse(BaseModel):
    id: str
    event_type: str
    actor: str
    target: str | None
    created_at: str


async def current_membership(db: AsyncSession, user: User) -> GuildMembership | None:
    return await db.scalar(select(GuildMembership).where(GuildMembership.user_id == user.id))


async def require_membership(db: AsyncSession, user: User) -> GuildMembership:
    membership = await current_membership(db, user)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator is not aligned with a guild")
    return membership


async def get_callsign(db: AsyncSession, user_id: str | None, anonymous: bool = False) -> str:
    if user_id is None:
        return "SYSTEM"
    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if anonymous or (profile and profile.anonymous_on_leaderboard):
        return "Anonymous Operator"
    return profile.callsign if profile and profile.callsign else "OPERATOR"


async def generate_invite_code(db: AsyncSession) -> str:
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(25):
        code = "".join(random.choice(alphabet) for _ in range(6))
        existing = await db.scalar(select(GuildInviteCode).where(GuildInviteCode.code == code))
        if existing is None:
            return code
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to generate guild code")


async def member_count(db: AsyncSession, guild_id: str) -> int:
    return await db.scalar(select(func.count()).select_from(GuildMembership).where(GuildMembership.guild_id == guild_id)) or 0


async def guild_xp(db: AsyncSession, guild_id: str) -> int:
    rows = await db.execute(
        select(CharacterProfile.xp)
        .join(GuildMembership, GuildMembership.user_id == CharacterProfile.user_id)
        .where(GuildMembership.guild_id == guild_id)
    )
    return int(sum(row[0] for row in rows) * 0.05)


async def serialize_guild(db: AsyncSession, guild: Guild, user: User | None = None, include_invite: bool = True) -> GuildResponse:
    role = None
    if user is not None:
        membership = await db.scalar(
            select(GuildMembership).where(GuildMembership.guild_id == guild.id, GuildMembership.user_id == user.id)
        )
        role = membership.role if membership else None

    invite_code = None
    if include_invite:
        invite = await db.scalar(
            select(GuildInviteCode).where(GuildInviteCode.guild_id == guild.id, GuildInviteCode.is_active.is_(True))
        )
        invite_code = invite.code if invite else None

    return GuildResponse(
        id=guild.id,
        name=guild.name,
        motto=guild.motto,
        role=role,
        invite_code=invite_code,
        member_count=await member_count(db, guild.id),
        guild_xp=await guild_xp(db, guild.id),
    )


async def add_moderation_event(
    db: AsyncSession,
    guild_id: str,
    actor_user_id: str | None,
    event_type: str,
    target_user_id: str | None = None,
    detail: str | None = None,
) -> None:
    db.add(
        GuildModerationEvent(
            guild_id=guild_id,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            event_type=event_type,
            payload={"detail": detail} if detail else {},
        )
    )


async def serialize_feed_event(db: AsyncSession, event: ActivityEvent) -> FeedEventResponse:
    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == event.user_id))
    payload = event.payload or {}
    return FeedEventResponse(
        id=event.id,
        event_type=event.event_type,
        operator="Anonymous Operator" if profile and profile.anonymous_on_leaderboard else profile.callsign if profile and profile.callsign else "OPERATOR",
        goal_title=payload.get("goal_title"),
        xp_awarded=payload.get("xp_awarded"),
        stat_key=payload.get("stat_key"),
        created_at=event.created_at.isoformat(),
    )


async def serialize_member(db: AsyncSession, membership: GuildMembership, current_user_id: str | None = None) -> GuildMemberResponse:
    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == membership.user_id))
    character = await db.scalar(select(CharacterProfile).where(CharacterProfile.user_id == membership.user_id))
    totals = await db.execute(
        select(
            func.count(Goal.id),
            func.count(Goal.id).filter(Goal.is_complete.is_(True)),
        ).where(Goal.user_id == membership.user_id)
    )
    total_goals, completed_goals = totals.one()
    completion_rate = round((completed_goals / total_goals) * 100, 1) if total_goals else 0.0
    return GuildMemberResponse(
        user_id=membership.user_id,
        callsign=profile.callsign if profile and profile.callsign else "OPERATOR",
        role=membership.role,
        xp=character.xp if character else 0,
        level=character.level if character else 1,
        completion_rate=completion_rate,
        anonymous_on_leaderboard=profile.anonymous_on_leaderboard if profile else False,
        is_current_user=membership.user_id == current_user_id,
        joined_at=membership.created_at.isoformat(),
    )


async def weekly_xp_for_user(db: AsyncSession, user_id: str) -> int:
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=now.weekday(), hours=now.hour, minutes=now.minute, seconds=now.second, microseconds=now.microsecond)
    result = await db.scalars(
        select(ActivityEvent)
        .where(ActivityEvent.user_id == user_id, ActivityEvent.event_type == "battle_reward", ActivityEvent.created_at >= week_start)
    )
    return sum((event.payload or {}).get("xp_awarded", 0) for event in result)


async def streak_for_user(db: AsyncSession, user_id: str) -> int:
    result = await db.scalars(
        select(ActivityEvent)
        .where(ActivityEvent.user_id == user_id, ActivityEvent.event_type == "battle_reward")
        .order_by(ActivityEvent.created_at.desc())
        .limit(60)
    )
    days = {event.created_at.date() for event in result}
    current = datetime.now(timezone.utc).date()
    streak = 0
    while current in days:
        streak += 1
        current -= timedelta(days=1)
    return streak


async def build_leaderboard(
    db: AsyncSession,
    memberships: list[GuildMembership] | None = None,
    metric: str = "total_xp",
    stat_key: str | None = None,
) -> list[LeaderboardEntryResponse]:
    user_ids = [membership.user_id for membership in memberships] if memberships is not None else None
    rows = await db.scalars(select(CharacterProfile).where(CharacterProfile.user_id.in_(user_ids)) if user_ids else select(CharacterProfile))
    characters = list(rows)
    entries: list[tuple[int, LeaderboardEntryResponse]] = []
    for character in characters:
        profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == character.user_id))
        weekly_xp = await weekly_xp_for_user(db, character.user_id)
        streak = await streak_for_user(db, character.user_id)
        stat_xp = None
        if stat_key:
            stat = await db.scalar(select(CharacterStat).where(CharacterStat.user_id == character.user_id, CharacterStat.stat_key == stat_key))
            stat_xp = stat.xp if stat else 0
        score = streak if metric == "streak" else stat_xp if metric == "stat" else weekly_xp
        entries.append(
            (
                score or 0,
                LeaderboardEntryResponse(
                    user_id=character.user_id,
                    display_name="Anonymous Operator"
                    if profile and profile.anonymous_on_leaderboard
                    else profile.callsign
                    if profile and profile.callsign
                    else "OPERATOR",
                    rank=0,
                    xp=character.xp,
                    weekly_xp=weekly_xp,
                    streak_length=streak,
                    stat_key=stat_key,
                    stat_xp=stat_xp,
                ),
            )
        )
    ranked = [entry for _, entry in sorted(entries, key=lambda item: item[0], reverse=True)]
    for index, entry in enumerate(ranked, start=1):
        entry.rank = index
    return ranked


async def reaction_counts(db: AsyncSession, message_id: str) -> dict[str, int]:
    result = await db.scalars(select(GuildChatReaction).where(GuildChatReaction.message_id == message_id))
    return dict(Counter(reaction.emoji for reaction in result))


def top_reaction(counts: dict[str, int]) -> tuple[str | None, int]:
    if not counts:
        return None, 0
    return max(counts.items(), key=lambda item: (item[1], item[0]))


async def refresh_reaction_trend(db: AsyncSession, message_id: str) -> GuildReactionTrend:
    counts = await reaction_counts(db, message_id)
    top_emoji, top_count = top_reaction(counts)
    trend = await db.scalar(select(GuildReactionTrend).where(GuildReactionTrend.message_id == message_id))
    if trend is None:
        trend = GuildReactionTrend(
            message_id=message_id,
            top_emoji=top_emoji,
            top_count=top_count,
            previous_top_emoji=None,
            previous_top_count=0,
            last_changed_at=now_utc(),
        )
    elif trend.top_emoji != top_emoji or trend.top_count != top_count:
        trend.previous_top_emoji = trend.top_emoji
        trend.previous_top_count = trend.top_count
        trend.top_emoji = top_emoji
        trend.top_count = top_count
        trend.last_changed_at = now_utc()
    db.add(trend)
    return trend


async def serialize_message(db: AsyncSession, message: GuildChatMessage, user: User) -> GuildMessageResponse:
    counts = await reaction_counts(db, message.id)
    my_reaction = await db.scalar(select(GuildChatReaction).where(GuildChatReaction.message_id == message.id, GuildChatReaction.user_id == user.id))
    trend = await refresh_reaction_trend(db, message.id)
    suggested = trend.top_emoji if trend.top_emoji else QUICK_EMOJI[0]
    return GuildMessageResponse(
        id=message.id,
        author_id=message.user_id,
        author=await get_callsign(db, message.user_id),
        body=message.body,
        goal_id=message.goal_id,
        task_ref=message.task_ref,
        created_at=message.created_at.isoformat(),
        reactions=counts,
        my_reaction=my_reaction.emoji if my_reaction else None,
        suggested_emoji=suggested,
        trend=ReactionTrendResponse(
            top_emoji=trend.top_emoji,
            top_count=trend.top_count,
            previous_top_emoji=trend.previous_top_emoji,
            previous_top_count=trend.previous_top_count,
            last_changed_at=trend.last_changed_at.isoformat() if trend.last_changed_at else None,
        ),
    )


async def require_owner(membership: GuildMembership) -> None:
    if membership.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the guild creator can perform this action")


async def require_moderator(membership: GuildMembership) -> None:
    if membership.role not in {"owner", "moderator"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Moderator access required")


@router.get("/status", response_model=GuildStatusResponse)
async def get_guild_status(user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]) -> GuildStatusResponse:
    membership = await current_membership(db, user)
    if membership is None:
        return GuildStatusResponse(aligned=False, guild=None)
    guild = await db.get(Guild, membership.guild_id)
    return GuildStatusResponse(aligned=guild is not None, guild=await serialize_guild(db, guild, user) if guild else None)


@router.post("/forge", response_model=GuildStatusResponse, status_code=status.HTTP_201_CREATED)
async def forge_guild(payload: GuildForgeRequest, user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]) -> GuildStatusResponse:
    if await current_membership(db, user) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Operator is already aligned with a guild")
    existing = await db.scalar(select(Guild).where(Guild.name == payload.name.strip()))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Guild name already exists")

    guild = Guild(owner_user_id=user.id, name=payload.name.strip(), motto=payload.motto.strip() if payload.motto else None)
    db.add(guild)
    await db.flush()
    db.add(GuildMembership(guild_id=guild.id, user_id=user.id, role="owner"))
    db.add(GuildInviteCode(guild_id=guild.id, code=await generate_invite_code(db), is_active=True))
    await add_moderation_event(db, guild.id, user.id, "guild_forged", user.id, "Creator founded the guild")
    await db.commit()
    await db.refresh(guild)
    return GuildStatusResponse(aligned=True, guild=await serialize_guild(db, guild, user))


@router.post("/join", response_model=GuildStatusResponse)
async def join_guild(payload: GuildJoinRequest, user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]) -> GuildStatusResponse:
    if await current_membership(db, user) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Operator is already aligned with a guild")
    invite = await db.scalar(select(GuildInviteCode).where(GuildInviteCode.code == payload.code, GuildInviteCode.is_active.is_(True)))
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guild code invalid")
    guild = await db.get(Guild, invite.guild_id)
    if guild is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guild not found")
    if await member_count(db, guild.id) >= GUILD_MAX_MEMBERS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Guild is at the 10-member limit")

    db.add(GuildMembership(guild_id=guild.id, user_id=user.id, role="member"))
    await add_moderation_event(db, guild.id, user.id, "member_joined", user.id)
    await db.commit()
    return GuildStatusResponse(aligned=True, guild=await serialize_guild(db, guild, user))


@router.get("/my-guild", response_model=Optional[GuildResponse])
async def my_guild(user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]) -> GuildResponse | None:
    membership = await current_membership(db, user)
    if membership is None:
        return None
    guild = await db.get(Guild, membership.guild_id)
    return await serialize_guild(db, guild, user) if guild else None


@router.get("/discover", response_model=list[GuildResponse])
async def discover_guilds(user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]) -> list[GuildResponse]:
    result = await db.scalars(select(Guild).order_by(Guild.created_at.desc()).limit(30))
    return [await serialize_guild(db, guild, user, include_invite=False) for guild in result]


@router.get("/overview", response_model=GuildOverviewResponse)
async def guild_overview(user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]) -> GuildOverviewResponse:
    membership = await require_membership(db, user)
    guild = await db.get(Guild, membership.guild_id)
    if guild is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guild not found")
    memberships = list(await db.scalars(select(GuildMembership).where(GuildMembership.guild_id == guild.id).order_by(GuildMembership.created_at.asc())))
    events = list(
        await db.scalars(
            select(GuildModerationEvent).where(GuildModerationEvent.guild_id == guild.id).order_by(GuildModerationEvent.created_at.desc()).limit(20)
        )
    )
    return GuildOverviewResponse(
        guild=await serialize_guild(db, guild, user),
        members=[await serialize_member(db, item, user.id) for item in memberships],
        leaderboard=await build_leaderboard(db, memberships),
        moderation_feed=[
            ModerationEventResponse(
                id=event.id,
                event_type=event.event_type,
                actor=await get_callsign(db, event.actor_user_id),
                target=await get_callsign(db, event.target_user_id) if event.target_user_id else None,
                created_at=event.created_at.isoformat(),
                detail=(event.payload or {}).get("detail"),
            )
            for event in events
        ],
    )


@router.get("/leaderboard/global", response_model=list[LeaderboardEntryResponse])
async def global_leaderboard(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    metric: Literal["total_xp", "streak", "stat"] = "total_xp",
    stat_key: str | None = None,
) -> list[LeaderboardEntryResponse]:
    return (await build_leaderboard(db, metric=metric, stat_key=stat_key))[:50]


@router.patch("/leaderboard/privacy", response_model=dict[str, bool])
async def update_leaderboard_privacy(
    payload: LeaderboardPrivacyRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, bool]:
    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    if profile is None:
        profile = UserProfile(user_id=user.id)
    profile.anonymous_on_leaderboard = payload.anonymous_on_leaderboard
    db.add(profile)
    await db.commit()
    return {"anonymous_on_leaderboard": profile.anonymous_on_leaderboard}


@router.get("/messages", response_model=list[GuildMessageResponse])
async def list_messages(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(default=None, max_length=120),
    member_id: str | None = None,
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    reaction: str | None = None,
) -> list[GuildMessageResponse]:
    membership = await require_membership(db, user)
    query = select(GuildChatMessage).where(GuildChatMessage.guild_id == membership.guild_id, GuildChatMessage.is_hidden.is_(False))
    if search:
        query = query.where(GuildChatMessage.body.ilike(f"%{search}%"))
    if member_id:
        query = query.where(GuildChatMessage.user_id == member_id)
    if from_time:
        query = query.where(GuildChatMessage.created_at >= from_time)
    if to_time:
        query = query.where(GuildChatMessage.created_at <= to_time)
    query = query.order_by(GuildChatMessage.created_at.desc()).limit(100)
    messages = list(await db.scalars(query))
    serialized = [await serialize_message(db, message, user) for message in reversed(messages)]
    if reaction:
        serialized = [message for message in serialized if message.trend.top_emoji == reaction]
    await db.commit()
    return serialized


@router.post("/messages", response_model=GuildMessageResponse, status_code=status.HTTP_201_CREATED)
async def post_message(
    payload: GuildMessageRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GuildMessageResponse:
    membership = await require_membership(db, user)
    if payload.goal_id is not None:
        goal = await db.scalar(select(Goal).where(Goal.id == payload.goal_id, Goal.user_id == user.id))
        if goal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal link not found")
    message = GuildChatMessage(
        guild_id=membership.guild_id,
        user_id=user.id,
        body=payload.body.strip(),
        goal_id=payload.goal_id,
        task_ref=payload.task_ref.strip() if payload.task_ref else None,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    response = await serialize_message(db, message, user)
    await db.commit()
    return response


@router.post("/messages/{message_id}/reaction", response_model=GuildMessageResponse)
async def toggle_reaction(
    message_id: str,
    payload: GuildReactionRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GuildMessageResponse:
    membership = await require_membership(db, user)
    message = await db.scalar(
        select(GuildChatMessage).where(GuildChatMessage.id == message_id, GuildChatMessage.guild_id == membership.guild_id, GuildChatMessage.is_hidden.is_(False))
    )
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    toggle = await db.scalar(select(GuildReactionToggle).where(GuildReactionToggle.message_id == message.id, GuildReactionToggle.user_id == user.id))
    now = now_utc()
    if toggle and now - toggle.last_toggled_at < timedelta(seconds=REACTION_RATE_LIMIT_SECONDS):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Reaction toggle rate limit exceeded")
    if toggle is None:
        toggle = GuildReactionToggle(message_id=message.id, user_id=user.id, last_toggled_at=now)
    else:
        toggle.last_toggled_at = now
    db.add(toggle)

    reaction = await db.scalar(select(GuildChatReaction).where(GuildChatReaction.message_id == message.id, GuildChatReaction.user_id == user.id))
    if reaction and reaction.emoji == payload.emoji:
        await db.delete(reaction)
    elif reaction:
        reaction.emoji = payload.emoji
        db.add(reaction)
    else:
        db.add(GuildChatReaction(message_id=message.id, user_id=user.id, emoji=payload.emoji))
    await refresh_reaction_trend(db, message.id)
    await db.commit()
    return await serialize_message(db, message, user)


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def hide_message(message_id: str, user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]) -> None:
    membership = await require_membership(db, user)
    await require_moderator(membership)
    message = await db.scalar(select(GuildChatMessage).where(GuildChatMessage.id == message_id, GuildChatMessage.guild_id == membership.guild_id))
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    message.is_hidden = True
    message.hidden_by_user_id = user.id
    message.hidden_at = now_utc()
    db.add(message)
    await add_moderation_event(db, membership.guild_id, user.id, "message_hidden", message.user_id, message.body[:120])
    await db.commit()


@router.patch("/members/{member_id}/role", response_model=GuildOverviewResponse)
async def update_member_role(
    member_id: str,
    payload: GuildRoleRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GuildOverviewResponse:
    membership = await require_membership(db, user)
    await require_owner(membership)
    target = await db.scalar(select(GuildMembership).where(GuildMembership.guild_id == membership.guild_id, GuildMembership.user_id == member_id))
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    if target.role == "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The creator cannot be demoted")
    if payload.role == "moderator":
        moderator_count = await db.scalar(
            select(func.count()).select_from(GuildMembership).where(GuildMembership.guild_id == membership.guild_id, GuildMembership.role == "moderator")
        )
        if moderator_count is not None and moderator_count >= GUILD_MAX_MODERATORS and target.role != "moderator":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Guild already has two moderators")
    target.role = payload.role
    db.add(target)
    await add_moderation_event(db, membership.guild_id, user.id, "promote" if payload.role == "moderator" else "demote", member_id)
    await db.commit()
    return await guild_overview(user, db)


@router.delete("/members/{member_id}", response_model=GuildOverviewResponse)
async def remove_member(member_id: str, user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]) -> GuildOverviewResponse:
    membership = await require_membership(db, user)
    await require_moderator(membership)
    target = await db.scalar(select(GuildMembership).where(GuildMembership.guild_id == membership.guild_id, GuildMembership.user_id == member_id))
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    if target.role == "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The creator cannot be removed")
    await db.execute(delete(GuildMembership).where(GuildMembership.id == target.id))
    await add_moderation_event(db, membership.guild_id, user.id, "kick", member_id)
    await db.commit()
    return await guild_overview(user, db)


@router.get("/global", response_model=list[FeedEventResponse])
async def global_feed(user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]) -> list[FeedEventResponse]:
    result = await db.scalars(
        select(ActivityEvent).where(ActivityEvent.event_type == "battle_reward").order_by(ActivityEvent.created_at.desc()).limit(50)
    )
    return [await serialize_feed_event(db, event) for event in result]


@router.get("/members", response_model=list[GuildMemberResponse])
async def list_members(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[GuildMemberResponse]:
    membership = await require_membership(db, user)
    result = await db.scalars(select(GuildMembership).where(GuildMembership.guild_id == membership.guild_id))
    return [
        GuildMemberResponse(user_id=member.user_id, operator=await operator_name(db, member.user_id) or "OPERATOR", role=member.role)
        for member in result
    ]


@router.get("/leaderboard", response_model=list[GuildLeaderboardEntry])
async def leaderboard(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[GuildLeaderboardEntry]:
    guilds = await db.scalars(select(Guild).order_by(Guild.created_at.desc()).limit(50))
    rows: list[GuildLeaderboardEntry] = []
    for guild in guilds:
        memberships = list(await db.scalars(select(GuildMembership).where(GuildMembership.guild_id == guild.id)))
        xp_sum = 0
        for member in memberships:
            character = await db.scalar(select(CharacterProfile).where(CharacterProfile.user_id == member.user_id))
            xp_sum += character.xp if character else 0
        rows.append(GuildLeaderboardEntry(guild_id=guild.id, name=guild.name, member_xp_sum=xp_sum, guild_xp=int(xp_sum * 0.05)))
    return sorted(rows, key=lambda row: row.guild_xp, reverse=True)


@router.post("/members/{target_user_id}/promote", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def promote_member(
    target_user_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    membership = await require_membership(db, user)
    if membership.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the guild creator can promote moderators")
    moderators = list(
        await db.scalars(select(GuildMembership).where(GuildMembership.guild_id == membership.guild_id, GuildMembership.role == "moderator"))
    )
    if len(moderators) >= 2:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Guild can only have two moderators")
    target = await db.scalar(select(GuildMembership).where(GuildMembership.guild_id == membership.guild_id, GuildMembership.user_id == target_user_id))
    if target is None or target.role == "owner":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not eligible")
    target.role = "moderator"
    db.add(target)
    await log_moderation(db, membership.guild_id, user.id, "promote", target_user_id)
    await db.commit()


@router.post("/members/{target_user_id}/demote", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def demote_member(
    target_user_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    membership = await require_membership(db, user)
    if membership.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the guild creator can demote moderators")
    target = await db.scalar(select(GuildMembership).where(GuildMembership.guild_id == membership.guild_id, GuildMembership.user_id == target_user_id))
    if target is None or target.role != "moderator":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Moderator not found")
    target.role = "member"
    db.add(target)
    await log_moderation(db, membership.guild_id, user.id, "demote", target_user_id)
    await db.commit()


@router.delete("/members/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def kick_member(
    target_user_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    membership = await require_membership(db, user)
    if not can_moderate(membership.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only moderators can remove members")
    target = await db.scalar(select(GuildMembership).where(GuildMembership.guild_id == membership.guild_id, GuildMembership.user_id == target_user_id))
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    if target.role == "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Moderators cannot remove the owner")
    await db.delete(target)
    await log_moderation(db, membership.guild_id, user.id, "kick", target_user_id)
    await db.commit()


@router.get("/chat", response_model=list[GuildChatResponse])
async def list_chat(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str | None = None,
    member_id: str | None = None,
    emoji: str | None = None,
) -> list[GuildChatResponse]:
    membership = await require_membership(db, user)
    query = select(GuildChatMessage).where(GuildChatMessage.guild_id == membership.guild_id, GuildChatMessage.hidden_at.is_(None))
    if member_id:
        query = query.where(GuildChatMessage.user_id == member_id)
    if q:
        query = query.where(GuildChatMessage.body.ilike(f"%{q}%"))
    if emoji:
        query = query.where(GuildChatMessage.top_emoji == emoji)
    result = await db.scalars(query.order_by(GuildChatMessage.created_at.desc()).limit(100))
    return [await serialize_chat_message(db, message) for message in result]


@router.post("/chat", response_model=GuildChatResponse, status_code=status.HTTP_201_CREATED)
async def post_chat(
    payload: GuildChatCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GuildChatResponse:
    membership = await require_membership(db, user)
    message = GuildChatMessage(guild_id=membership.guild_id, user_id=user.id, body=payload.body.strip(), goal_id=payload.goal_id)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return await serialize_chat_message(db, message)


@router.put("/chat/{message_id}/reaction", response_model=GuildChatResponse)
async def set_reaction(
    message_id: str,
    payload: ReactionPayload,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GuildChatResponse:
    membership = await require_membership(db, user)
    message = await db.scalar(select(GuildChatMessage).where(GuildChatMessage.id == message_id, GuildChatMessage.guild_id == membership.guild_id))
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    reaction = await db.scalar(select(GuildChatReaction).where(GuildChatReaction.message_id == message.id, GuildChatReaction.user_id == user.id))
    if reaction is None:
        reaction = GuildChatReaction(message_id=message.id, user_id=user.id, emoji=payload.emoji)
    else:
        reaction.emoji = payload.emoji
    db.add(reaction)
    await db.flush()
    await update_message_reaction_baseline(db, message)
    await db.commit()
    await db.refresh(message)
    return await serialize_chat_message(db, message)


@router.delete("/chat/{message_id}/reaction", response_model=GuildChatResponse)
async def clear_reaction(
    message_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GuildChatResponse:
    membership = await require_membership(db, user)
    message = await db.scalar(select(GuildChatMessage).where(GuildChatMessage.id == message_id, GuildChatMessage.guild_id == membership.guild_id))
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    reaction = await db.scalar(select(GuildChatReaction).where(GuildChatReaction.message_id == message.id, GuildChatReaction.user_id == user.id))
    if reaction is not None:
        await db.delete(reaction)
        await db.flush()
        await update_message_reaction_baseline(db, message)
        await db.commit()
    return await serialize_chat_message(db, message)


@router.delete("/chat/{message_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def hide_chat_message(
    message_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    membership = await require_membership(db, user)
    if not can_moderate(membership.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only moderators can hide messages")
    message = await db.scalar(select(GuildChatMessage).where(GuildChatMessage.id == message_id, GuildChatMessage.guild_id == membership.guild_id))
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    message.hidden_at = now_utc()
    message.hidden_by_user_id = user.id
    db.add(message)
    await log_moderation(db, membership.guild_id, user.id, "hide_message", message.user_id, {"message_id": message.id})
    await db.commit()


@router.get("/moderation", response_model=list[ModerationEventResponse])
async def moderation_feed(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ModerationEventResponse]:
    membership = await require_membership(db, user)
    events = await db.scalars(
        select(GuildModerationEvent).where(GuildModerationEvent.guild_id == membership.guild_id).order_by(GuildModerationEvent.created_at.desc()).limit(100)
    )
    return [
        ModerationEventResponse(
            id=event.id,
            event_type=event.event_type,
            actor=await operator_name(db, event.actor_user_id) or "OPERATOR",
            target=await operator_name(db, event.target_user_id),
            created_at=event.created_at.isoformat(),
        )
        for event in events
    ]
