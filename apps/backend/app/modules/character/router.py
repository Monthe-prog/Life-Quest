from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Achievement, CharacterProfile, CharacterStat, SkillUnlock, User, UserProfile

router = APIRouter()

CharacterClass = Literal["Cyber-Monk", "Netrunner", "Dreadnought"]

CLASS_BONUSES: dict[str, dict[str, int]] = {
    "Cyber-Monk": {"wisdom": 2, "charisma": 1},
    "Netrunner": {"intellect": 2, "wealth": 1},
    "Dreadnought": {"strength": 2, "wisdom": 1},
}

VALID_HEADS = {"visor", "halo", "hood"}
VALID_BODIES = {"cloak", "armor", "jacket"}
VALID_GEAR = {"blade", "deck", "gauntlet"}


class CustomizerUpdate(BaseModel):
    character_class: CharacterClass | None = None
    head_cosmetic: str | None = None
    body_cosmetic: str | None = None
    gear_cosmetic: str | None = None


class StatResponse(BaseModel):
    stat_key: str
    label: str
    level: int
    xp: int
    class_bonus: int
    effective_level: int


class SkillResponse(BaseModel):
    skill_key: str
    label: str
    stat_key: str
    required_level: int
    unlocked: bool


class AchievementResponse(BaseModel):
    achievement_key: str
    label: str
    unlocked: bool


class CharacterProfileResponse(BaseModel):
    callsign: str
    character_class: str
    head_cosmetic: str
    body_cosmetic: str
    gear_cosmetic: str
    level: int
    xp: int
    stats: list[StatResponse]
    skills: list[SkillResponse]
    achievements: list[AchievementResponse]


def skill_label(skill_key: str) -> str:
    return skill_key.replace("_", " ").upper()


async def load_character_payload(db: AsyncSession, user: User) -> CharacterProfileResponse:
    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    character = await db.scalar(select(CharacterProfile).where(CharacterProfile.user_id == user.id))
    if character is None:
        character = CharacterProfile(user_id=user.id)
        db.add(character)
        await db.commit()
        await db.refresh(character)

    stats_result = await db.scalars(select(CharacterStat).where(CharacterStat.user_id == user.id).order_by(CharacterStat.stat_key.asc()))
    stats = list(stats_result)
    bonuses = CLASS_BONUSES.get(character.character_class, {})
    effective_stats = {stat.stat_key: stat.level + bonuses.get(stat.stat_key, 0) for stat in stats}

    skill_result = await db.scalars(select(SkillUnlock).where(SkillUnlock.user_id == user.id).order_by(SkillUnlock.required_level.asc()))
    skills = [
        SkillResponse(
            skill_key=skill.skill_key,
            label=skill_label(skill.skill_key),
            stat_key=skill.stat_key,
            required_level=skill.required_level,
            unlocked=skill.unlocked_at is not None or effective_stats.get(skill.stat_key, 0) >= skill.required_level,
        )
        for skill in skill_result
    ]

    achievement_result = await db.scalars(select(Achievement).where(Achievement.user_id == user.id).order_by(Achievement.created_at.asc()))
    achievements = [
        AchievementResponse(
            achievement_key=achievement.achievement_key,
            label=achievement.label,
            unlocked=achievement.unlocked_at is not None,
        )
        for achievement in achievement_result
    ]

    return CharacterProfileResponse(
        callsign=profile.callsign if profile and profile.callsign else "OPERATOR",
        character_class=character.character_class,
        head_cosmetic=character.head_cosmetic,
        body_cosmetic=character.body_cosmetic,
        gear_cosmetic=character.gear_cosmetic,
        level=character.level,
        xp=character.xp,
        stats=[
            StatResponse(
                stat_key=stat.stat_key,
                label=stat.label,
                level=stat.level,
                xp=stat.xp,
                class_bonus=bonuses.get(stat.stat_key, 0),
                effective_level=stat.level + bonuses.get(stat.stat_key, 0),
            )
            for stat in stats
        ],
        skills=skills,
        achievements=achievements,
    )


@router.get("/profile", response_model=CharacterProfileResponse)
async def get_profile(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CharacterProfileResponse:
    return await load_character_payload(db, user)


@router.patch("/customizer", response_model=CharacterProfileResponse)
async def update_customizer(
    payload: CustomizerUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CharacterProfileResponse:
    character = await db.scalar(select(CharacterProfile).where(CharacterProfile.user_id == user.id))
    if character is None:
        character = CharacterProfile(user_id=user.id)

    if payload.character_class is not None:
        character.character_class = payload.character_class
    if payload.head_cosmetic is not None:
        if payload.head_cosmetic not in VALID_HEADS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid head cosmetic")
        character.head_cosmetic = payload.head_cosmetic
    if payload.body_cosmetic is not None:
        if payload.body_cosmetic not in VALID_BODIES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid body cosmetic")
        character.body_cosmetic = payload.body_cosmetic
    if payload.gear_cosmetic is not None:
        if payload.gear_cosmetic not in VALID_GEAR:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid gear cosmetic")
        character.gear_cosmetic = payload.gear_cosmetic

    db.add(character)
    await db.commit()
    return await load_character_payload(db, user)


@router.get("/skills", response_model=list[SkillResponse])
async def get_skills(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SkillResponse]:
    return (await load_character_payload(db, user)).skills


@router.get("/achievements", response_model=list[AchievementResponse])
async def get_achievements(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AchievementResponse]:
    return (await load_character_payload(db, user)).achievements
