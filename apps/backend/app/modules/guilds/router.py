from __future__ import annotations

import random
import string
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import ActivityEvent, Guild, GuildInviteCode, GuildMembership, User, UserProfile

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


async def current_membership(db: AsyncSession, user: User) -> GuildMembership | None:
    return await db.scalar(select(GuildMembership).where(GuildMembership.user_id == user.id))


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
