from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import BossBattle, CharacterProfile, Goal, Quest, QuestStep, User, now_utc

router = APIRouter()


class QuestCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=2000)
    skill_key: Optional[str] = Field(default=None, max_length=80)
    reward_xp: int = Field(default=100, ge=0)
    steps: list[str] = Field(default_factory=list, max_length=12)
    expires_at: Optional[datetime] = None


class QuestStepResponse(BaseModel):
    id: str
    title: str
    completed: bool


class QuestResponse(BaseModel):
    id: str
    title: str
    description: str
    skill_key: Optional[str]
    status: str
    reward_xp: int
    claimed: bool
    expires_at: Optional[str]
    steps: list[QuestStepResponse]


class BossCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    goal_id: Optional[str] = None
    required_count: int = Field(default=1, ge=1)
    reward_xp: int = Field(default=500, ge=0)


class BossResponse(BaseModel):
    id: str
    title: str
    goal_id: Optional[str]
    required_count: int
    progress_count: int
    reward_xp: int
    status: str
    percent_complete: int
    claimed: bool


async def serialize_quest(db: AsyncSession, quest: Quest) -> QuestResponse:
    steps = await db.scalars(select(QuestStep).where(QuestStep.quest_id == quest.id).order_by(QuestStep.created_at.asc()))
    return QuestResponse(
        id=quest.id,
        title=quest.title,
        description=quest.description,
        skill_key=quest.skill_key,
        status=quest.status,
        reward_xp=quest.reward_xp,
        claimed=quest.claimed_at is not None,
        expires_at=quest.expires_at.isoformat() if quest.expires_at else None,
        steps=[QuestStepResponse(id=step.id, title=step.title, completed=step.completed_at is not None) for step in steps],
    )


def serialize_boss(boss: BossBattle) -> BossResponse:
    percent = int(min(100, (boss.progress_count / boss.required_count) * 100)) if boss.required_count else 0
    return BossResponse(
        id=boss.id,
        title=boss.title,
        goal_id=boss.goal_id,
        required_count=boss.required_count,
        progress_count=boss.progress_count,
        reward_xp=boss.reward_xp,
        status=boss.status,
        percent_complete=percent,
        claimed=boss.claimed_at is not None,
    )


async def get_quest(db: AsyncSession, user: User, quest_id: str) -> Quest:
    quest = await db.scalar(select(Quest).where(Quest.id == quest_id, Quest.user_id == user.id))
    if quest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quest not found")
    return quest


async def get_boss(db: AsyncSession, user: User, boss_id: str) -> BossBattle:
    boss = await db.scalar(select(BossBattle).where(BossBattle.id == boss_id, BossBattle.user_id == user.id))
    if boss is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Boss battle not found")
    return boss


async def award_xp(db: AsyncSession, user: User, amount: int) -> None:
    character = await db.scalar(select(CharacterProfile).where(CharacterProfile.user_id == user.id))
    if character is None:
        return
    character.xp += amount
    character.level = max(1, (character.xp // 1000) + 1)
    db.add(character)


@router.get("", response_model=list[QuestResponse])
async def list_quests(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[QuestResponse]:
    result = await db.scalars(select(Quest).where(Quest.user_id == user.id).order_by(Quest.created_at.desc()))
    return [await serialize_quest(db, quest) for quest in result]


@router.post("", response_model=QuestResponse, status_code=status.HTTP_201_CREATED)
async def create_quest(
    payload: QuestCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuestResponse:
    quest = Quest(
        user_id=user.id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        skill_key=payload.skill_key,
        reward_xp=payload.reward_xp,
        expires_at=payload.expires_at,
    )
    db.add(quest)
    await db.flush()
    for step in payload.steps:
        if step.strip():
            db.add(QuestStep(quest_id=quest.id, title=step.strip()))
    await db.commit()
    await db.refresh(quest)
    return await serialize_quest(db, quest)


@router.patch("/{quest_id}/steps/{step_id}/complete", response_model=QuestResponse)
async def complete_quest_step(
    quest_id: str,
    step_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuestResponse:
    quest = await get_quest(db, user, quest_id)
    step = await db.scalar(select(QuestStep).where(QuestStep.id == step_id, QuestStep.quest_id == quest.id))
    if step is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quest step not found")
    step.completed_at = now_utc()
    db.add(step)
    await db.commit()
    return await serialize_quest(db, quest)


@router.patch("/{quest_id}/abandon", response_model=QuestResponse)
async def abandon_quest(
    quest_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuestResponse:
    quest = await get_quest(db, user, quest_id)
    quest.status = "abandoned"
    db.add(quest)
    await db.commit()
    return await serialize_quest(db, quest)


@router.patch("/{quest_id}/claim", response_model=QuestResponse)
async def claim_quest(
    quest_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuestResponse:
    quest = await get_quest(db, user, quest_id)
    steps = list(await db.scalars(select(QuestStep).where(QuestStep.quest_id == quest.id)))
    if quest.status != "active" or quest.claimed_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Quest cannot be claimed in its current state")
    if steps and any(step.completed_at is None for step in steps):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Complete all quest steps before claiming reward")
    quest.status = "claimed"
    quest.claimed_at = now_utc()
    await award_xp(db, user, quest.reward_xp)
    db.add(quest)
    await db.commit()
    return await serialize_quest(db, quest)


@router.get("/bosses", response_model=list[BossResponse])
async def list_bosses(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[BossResponse]:
    result = await db.scalars(select(BossBattle).where(BossBattle.user_id == user.id).order_by(BossBattle.created_at.desc()))
    return [serialize_boss(boss) for boss in result]


@router.post("/bosses", response_model=BossResponse, status_code=status.HTTP_201_CREATED)
async def create_boss(
    payload: BossCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BossResponse:
    if payload.goal_id is not None:
        goal = await db.scalar(select(Goal).where(Goal.id == payload.goal_id, Goal.user_id == user.id))
        if goal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked goal not found")
    boss = BossBattle(
        user_id=user.id,
        goal_id=payload.goal_id,
        title=payload.title.strip(),
        required_count=payload.required_count,
        reward_xp=payload.reward_xp,
    )
    db.add(boss)
    await db.commit()
    await db.refresh(boss)
    return serialize_boss(boss)


@router.patch("/bosses/{boss_id}/claim", response_model=BossResponse)
async def claim_boss(
    boss_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BossResponse:
    boss = await get_boss(db, user, boss_id)
    if boss.progress_count < boss.required_count:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Boss is still alive")
    if boss.claimed_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Boss reward already claimed")
    boss.status = "claimed"
    boss.claimed_at = now_utc()
    await award_xp(db, user, boss.reward_xp)
    db.add(boss)
    await db.commit()
    await db.refresh(boss)
    return serialize_boss(boss)
