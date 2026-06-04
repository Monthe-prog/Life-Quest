from __future__ import annotations

import random
import string
from collections import Counter
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import (
    ActivityEvent,
    CharacterProfile,
    Guild,
    GuildChatMessage,
    GuildChatReaction,
    GuildInviteCode,
    GuildMembership,
    GuildModerationEvent,
    User,
    UserProfile,
    now_utc,
)

router = APIRouter()


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


class GuildResponse(BaseModel):
    id: str
    name: str
    motto: str | None
    role: str | None = None
    invite_code: str | None = None


class GuildStatusResponse(BaseModel):
    aligned: bool
    guild: GuildResponse | None


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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Join a guild first")
    return membership


def can_moderate(role: str) -> bool:
    return role in {"owner", "moderator"}


async def operator_name(db: AsyncSession, user_id: str | None) -> str | None:
    if user_id is None:
        return None
    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    return profile.callsign if profile and profile.callsign else "OPERATOR"


async def generate_invite_code(db: AsyncSession) -> str:
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(25):
        code = "".join(random.choice(alphabet) for _ in range(6))
        existing = await db.scalar(select(GuildInviteCode).where(GuildInviteCode.code == code))
        if existing is None:
            return code
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to generate guild code")


async def serialize_guild(db: AsyncSession, guild: Guild, user: User | None = None) -> GuildResponse:
    role = None
    if user is not None:
        membership = await db.scalar(
            select(GuildMembership).where(GuildMembership.guild_id == guild.id, GuildMembership.user_id == user.id)
        )
        role = membership.role if membership else None

    invite = await db.scalar(
        select(GuildInviteCode).where(GuildInviteCode.guild_id == guild.id, GuildInviteCode.is_active.is_(True))
    )
    return GuildResponse(id=guild.id, name=guild.name, motto=guild.motto, role=role, invite_code=invite.code if invite else None)


async def serialize_feed_event(db: AsyncSession, event: ActivityEvent) -> FeedEventResponse:
    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == event.user_id))
    payload = event.payload or {}
    return FeedEventResponse(
        id=event.id,
        event_type=event.event_type,
        operator=profile.callsign if profile and profile.callsign else "OPERATOR",
        goal_title=payload.get("goal_title"),
        xp_awarded=payload.get("xp_awarded"),
        stat_key=payload.get("stat_key"),
        created_at=event.created_at.isoformat(),
    )


async def reaction_counts(db: AsyncSession, message_id: str) -> dict[str, int]:
    reactions = await db.scalars(select(GuildChatReaction).where(GuildChatReaction.message_id == message_id))
    return dict(Counter(reaction.emoji for reaction in reactions))


async def update_message_reaction_baseline(db: AsyncSession, message: GuildChatMessage) -> None:
    counts = await reaction_counts(db, message.id)
    top_emoji = None
    top_count = 0
    if counts:
        top_emoji, top_count = max(counts.items(), key=lambda item: item[1])
    if top_emoji != message.top_emoji or top_count != message.top_emoji_count:
        message.previous_top_emoji = message.top_emoji
        message.previous_top_emoji_count = message.top_emoji_count
        message.top_emoji = top_emoji
        message.top_emoji_count = top_count
        message.trend_changed_at = now_utc()
        db.add(message)


async def serialize_chat_message(db: AsyncSession, message: GuildChatMessage) -> GuildChatResponse:
    counts = await reaction_counts(db, message.id)
    return GuildChatResponse(
        id=message.id,
        body=message.body,
        operator=await operator_name(db, message.user_id) or "OPERATOR",
        user_id=message.user_id,
        goal_id=message.goal_id,
        hidden=message.hidden_at is not None,
        reaction_counts=counts,
        top_emoji=message.top_emoji,
        top_emoji_count=message.top_emoji_count,
        previous_top_emoji=message.previous_top_emoji,
        previous_top_emoji_count=message.previous_top_emoji_count,
        trend_changed_at=message.trend_changed_at.isoformat() if message.trend_changed_at else None,
        created_at=message.created_at.isoformat(),
    )


async def log_moderation(
    db: AsyncSession,
    guild_id: str,
    actor_id: str,
    event_type: str,
    target_id: str | None = None,
    payload: dict | None = None,
) -> None:
    db.add(
        GuildModerationEvent(
            guild_id=guild_id,
            actor_user_id=actor_id,
            target_user_id=target_id,
            event_type=event_type,
            payload=payload or {},
        )
    )


@router.get("/status", response_model=GuildStatusResponse)
async def get_guild_status(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GuildStatusResponse:
    membership = await current_membership(db, user)
    if membership is None:
        return GuildStatusResponse(aligned=False, guild=None)
    guild = await db.get(Guild, membership.guild_id)
    return GuildStatusResponse(aligned=guild is not None, guild=await serialize_guild(db, guild, user) if guild else None)


@router.post("/forge", response_model=GuildStatusResponse, status_code=status.HTTP_201_CREATED)
async def forge_guild(
    payload: GuildForgeRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GuildStatusResponse:
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
    await db.commit()
    await db.refresh(guild)
    return GuildStatusResponse(aligned=True, guild=await serialize_guild(db, guild, user))


@router.post("/join", response_model=GuildStatusResponse)
async def join_guild(
    payload: GuildJoinRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GuildStatusResponse:
    if await current_membership(db, user) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Operator is already aligned with a guild")
    invite = await db.scalar(select(GuildInviteCode).where(GuildInviteCode.code == payload.code, GuildInviteCode.is_active.is_(True)))
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guild code invalid or already consumed")
    guild = await db.get(Guild, invite.guild_id)
    if guild is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guild not found")

    invite.is_active = False
    db.add(invite)
    db.add(GuildMembership(guild_id=guild.id, user_id=user.id, role="member"))
    await db.commit()
    return GuildStatusResponse(aligned=True, guild=await serialize_guild(db, guild, user))


@router.get("/my-guild", response_model=Optional[GuildResponse])
async def my_guild(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GuildResponse | None:
    membership = await current_membership(db, user)
    if membership is None:
        return None
    guild = await db.get(Guild, membership.guild_id)
    return await serialize_guild(db, guild, user) if guild else None


@router.get("/discover", response_model=list[GuildResponse])
async def discover_guilds(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[GuildResponse]:
    result = await db.scalars(select(Guild).order_by(Guild.created_at.desc()).limit(30))
    return [await serialize_guild(db, guild, user) for guild in result]


@router.get("/global", response_model=list[FeedEventResponse])
async def global_feed(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[FeedEventResponse]:
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
