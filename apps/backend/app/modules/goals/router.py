from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Achievement, ActivityEvent, BossBattle, CharacterProfile, CharacterStat, Goal, SkillUnlock, User
from app.modules.oracle.service import oracle_service

router = APIRouter()

GoalHorizon = Literal["five_year", "yearly", "monthly", "weekly", "daily_part_1", "daily_part_2"]

HORIZON_ORDER: list[GoalHorizon] = [
    "five_year",
    "yearly",
    "monthly",
    "weekly",
    "daily_part_1",
    "daily_part_2",
]

CHILD_HORIZON: dict[str, GoalHorizon] = {
    "five_year": "yearly",
    "yearly": "monthly",
    "monthly": "weekly",
    "weekly": "daily_part_1",
    "daily_part_1": "daily_part_2",
}

XP_BY_HORIZON = {
    "daily_part_1": 50,
    "daily_part_2": 50,
    "weekly": 150,
    "monthly": 350,
    "yearly": 750,
    "five_year": 1200,
}

SKILL_XP_MULTIPLIER_BY_TIER = {
    2: 1.05,
    5: 1.08,
    8: 1.12,
    12: 1.16,
    18: 1.22,
}

STAT_KEYWORDS = {
    "strength": ["gym", "run", "fitness", "health", "lift", "sleep", "diet", "workout", "body"],
    "wealth": ["money", "career", "finance", "business", "client", "sales", "income", "job", "invest"],
    "intellect": ["read", "study", "learn", "course", "code", "skill", "write", "research", "book"],
    "wisdom": ["mind", "meditate", "journal", "therapy", "focus", "calm", "spirit", "reflect"],
    "charisma": ["friend", "family", "date", "network", "call", "relationship", "social", "team"],
}


class GoalCreate(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    horizon: GoalHorizon
    parent_id: str | None = None
    part: str | None = None
    target_count: int = Field(default=1, ge=1, le=999)
    priority: int = Field(default=0, ge=0, le=5)


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=240)
    target_count: int | None = Field(default=None, ge=1, le=999)
    priority: int | None = Field(default=None, ge=0, le=5)
    is_complete: bool | None = None


class GoalProgressChange(BaseModel):
    delta: int = Field(ge=-99, le=99)


class GoalResponse(BaseModel):
    id: str
    parent_id: str | None
    title: str
    horizon: str
    part: str | None
    target_count: int
    completed_count: int
    priority: int
    is_complete: bool

    model_config = {"from_attributes": True}


class GoalListResponse(BaseModel):
    goals: list[GoalResponse]
    grouped: dict[str, list[GoalResponse]]


class BreakdownResponse(BaseModel):
    parent: GoalResponse
    child_horizon: str
    tasks: list[str]


class BreakdownAcceptRequest(BaseModel):
    tasks: list[str] = Field(min_length=1, max_length=10)


class BreakdownAcceptResponse(BaseModel):
    parent: GoalResponse
    children: list[GoalResponse]


class BattleEventResponse(BaseModel):
    goal_id: str
    goal_title: str
    xp_awarded: int
    boss_damage: int
    stat_key: str
    leveled_up: bool
    achievement_unlocked: str | None = None


class GoalProgressResponse(BaseModel):
    goal: GoalResponse
    battle_event: BattleEventResponse | None = None


async def get_owned_goal(db: AsyncSession, user: User, goal_id: str) -> Goal:
    goal = await db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user.id))
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return goal


def serialize_goal(goal: Goal) -> GoalResponse:
    return GoalResponse.model_validate(goal)


def group_goals(goals: list[Goal]) -> dict[str, list[GoalResponse]]:
    grouped = {horizon: [] for horizon in HORIZON_ORDER}
    for goal in goals:
        grouped.setdefault(goal.horizon, []).append(serialize_goal(goal))
    return grouped


def infer_stat_key(title: str) -> str:
    lowered = title.lower()
    for stat_key, keywords in STAT_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return stat_key
    return "intellect"


async def award_completion_reward(db: AsyncSession, user: User, goal: Goal) -> BattleEventResponse | None:
    if goal.rewarded_at is not None or not goal.is_complete:
        return None

    stat_key = infer_stat_key(goal.title)
    base_xp = XP_BY_HORIZON.get(goal.horizon, 50) + (goal.priority * 25)
    character = await db.scalar(select(CharacterProfile).where(CharacterProfile.user_id == user.id))
    if character is None:
        character = CharacterProfile(user_id=user.id)

    before_level = character.level
    character.xp += xp_awarded
    character.level = max(1, (character.xp // 1000) + 1)

    stat = await db.scalar(select(CharacterStat).where(CharacterStat.user_id == user.id, CharacterStat.stat_key == stat_key))
    stat_level = stat.level if stat is not None else 0
    unlocked_skills = await db.scalars(
        select(SkillUnlock).where(
            SkillUnlock.user_id == user.id,
            SkillUnlock.stat_key == stat_key,
            SkillUnlock.required_level <= stat_level,
        )
    )
    skill_multiplier = 1.0
    for skill in unlocked_skills:
        skill_multiplier += SKILL_XP_MULTIPLIER_BY_TIER.get(skill.required_level, 1.03) - 1.0

    streak_multiplier = 1.1 if goal.horizon in {"daily_part_1", "daily_part_2"} and goal.priority > 0 else 1.0
    xp_awarded = max(0, int(round(base_xp * skill_multiplier * streak_multiplier)))

    if stat is not None:
        stat.xp += xp_awarded
        stat.level = stat.xp // 500
        db.add(stat)

    achievement_unlocked: str | None = None
    if before_level < character.level:
        achievement = await db.scalar(
            select(Achievement).where(Achievement.user_id == user.id, Achievement.achievement_key == "first_level_up")
        )
        if achievement is not None and achievement.unlocked_at is None:
            achievement.unlocked_at = datetime.now(timezone.utc)
            achievement_unlocked = achievement.label
            db.add(achievement)

    if goal.priority >= 3:
        achievement = await db.scalar(
            select(Achievement).where(Achievement.user_id == user.id, Achievement.achievement_key == "boss_slayer")
        )
        if achievement is not None and achievement.unlocked_at is None:
            achievement.unlocked_at = datetime.now(timezone.utc)
            achievement_unlocked = achievement.label
            db.add(achievement)

    bosses = await db.scalars(
        select(BossBattle).where(
            BossBattle.user_id == user.id,
            BossBattle.goal_id == goal.id,
            BossBattle.status == "active",
        )
    )
    for boss in bosses:
        boss.progress_count = min(boss.required_count, boss.progress_count + 1)
        if boss.progress_count >= boss.required_count:
            boss.status = "victory_ready"
        db.add(boss)

    goal.rewarded_at = datetime.now(timezone.utc)
    event_payload = {
        "goal_id": goal.id,
        "goal_title": goal.title,
        "xp_awarded": xp_awarded,
        "boss_damage": min(100, 25 + goal.priority * 15),
        "stat_key": stat_key,
        "leveled_up": character.level > before_level,
        "achievement_unlocked": achievement_unlocked,
    }
    db.add(character)
    db.add(goal)
    db.add(ActivityEvent(user_id=user.id, goal_id=goal.id, event_type="battle_reward", payload=event_payload))
    return BattleEventResponse(**event_payload)


@router.get("", response_model=GoalListResponse)
async def list_goals(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GoalListResponse:
    result = await db.scalars(select(Goal).where(Goal.user_id == user.id).order_by(Goal.created_at.asc()))
    goals = list(result)
    return GoalListResponse(goals=[serialize_goal(goal) for goal in goals], grouped=group_goals(goals))


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    payload: GoalCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GoalResponse:
    if payload.parent_id is not None:
        await get_owned_goal(db, user, payload.parent_id)

    part = payload.part
    if payload.horizon == "daily_part_1":
        part = part or "morning"
    if payload.horizon == "daily_part_2":
        part = part or "evening"

    goal = Goal(
        user_id=user.id,
        parent_id=payload.parent_id,
        title=payload.title.strip(),
        horizon=payload.horizon,
        part=part,
        target_count=payload.target_count,
        completed_count=0,
        priority=payload.priority,
        is_complete=False,
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return serialize_goal(goal)


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: str,
    payload: GoalUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GoalResponse:
    goal = await get_owned_goal(db, user, goal_id)
    if payload.title is not None:
        goal.title = payload.title.strip()
    if payload.target_count is not None:
        goal.target_count = payload.target_count
        goal.completed_count = min(goal.completed_count, goal.target_count)
    if payload.priority is not None:
        goal.priority = payload.priority
    if payload.is_complete is not None:
        goal.is_complete = payload.is_complete
        if payload.is_complete:
            goal.completed_count = goal.target_count

    if goal.completed_count >= goal.target_count:
        goal.is_complete = True

    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return serialize_goal(goal)


@router.post("/{goal_id}/progress", response_model=GoalProgressResponse)
async def change_progress(
    goal_id: str,
    payload: GoalProgressChange,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GoalProgressResponse:
    goal = await get_owned_goal(db, user, goal_id)
    goal.completed_count = max(0, min(goal.target_count, goal.completed_count + payload.delta))
    goal.is_complete = goal.completed_count >= goal.target_count
    battle_event = await award_completion_reward(db, user, goal)
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return GoalProgressResponse(goal=serialize_goal(goal), battle_event=battle_event)


@router.post("/{goal_id}/children", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def spawn_child_goal(
    goal_id: str,
    payload: GoalCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GoalResponse:
    await get_owned_goal(db, user, goal_id)
    child_payload = payload.model_copy(update={"parent_id": goal_id})
    return await create_goal(child_payload, user, db)


@router.post("/{goal_id}/breakdown", response_model=BreakdownResponse)
async def oracle_breakdown(
    goal_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BreakdownResponse:
    parent = await get_owned_goal(db, user, goal_id)
    child_horizon = CHILD_HORIZON.get(parent.horizon)
    if child_horizon is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Oracle breakdown is only available for goals above evening daily tasks.",
        )

    oracle_result = await oracle_service.breakdown_goal(parent.title, parent.horizon, child_horizon)
    tasks = oracle_service.parse_tasks(oracle_result.text, parent.title)
    return BreakdownResponse(parent=serialize_goal(parent), child_horizon=child_horizon, tasks=tasks)


@router.post("/{goal_id}/breakdown/accept", response_model=BreakdownAcceptResponse, status_code=status.HTTP_201_CREATED)
async def accept_oracle_breakdown(
    goal_id: str,
    payload: BreakdownAcceptRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BreakdownAcceptResponse:
    parent = await get_owned_goal(db, user, goal_id)
    child_horizon = CHILD_HORIZON.get(parent.horizon)
    if child_horizon is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Oracle breakdown is only available for goals above evening daily tasks.",
        )

    children: list[Goal] = []
    for index, title in enumerate(payload.tasks, start=1):
        title = title.strip()
        if not title:
            continue
        child = Goal(
            user_id=user.id,
            parent_id=parent.id,
            title=title,
            horizon=child_horizon,
            part="morning" if child_horizon == "daily_part_1" else "evening" if child_horizon == "daily_part_2" else None,
            target_count=1,
            completed_count=0,
            priority=max(parent.priority, 1) if index == 1 else parent.priority,
            is_complete=False,
        )
        db.add(child)
        children.append(child)

    await db.commit()
    for child in children:
        await db.refresh(child)

    return BreakdownResponse(parent=serialize_goal(parent), children=[serialize_goal(child) for child in children])
