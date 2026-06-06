from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import CalendarBlock, Goal, User, UserProfile, now_utc

router = APIRouter()

SCHEDULE_START_HOUR = 7
SCHEDULE_END_HOUR = 22
PLANNER_DAYS = range(0, 6)
DAILY_MAX_HOURS = 8
SUNDAY_MAX_HOURS = 3
MAX_BLOCK_HOURS = 3
FULLNESS_WARNING_RATIO = 0.7


class CalendarBlockCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    day_of_week: int = Field(ge=0, le=6)
    start_hour: int = Field(ge=SCHEDULE_START_HOUR, le=SCHEDULE_END_HOUR - 1)
    end_hour: int = Field(ge=SCHEDULE_START_HOUR + 1, le=SCHEDULE_END_HOUR)
    goal_id: str | None = None
    is_recurring: bool = False
    recurrence_pattern: str | None = Field(default=None, max_length=80)
    alignment_status: str = Field(default="unknown", max_length=24)

    @model_validator(mode="after")
    def validate_time_range(self) -> "CalendarBlockCreate":
        if self.end_hour <= self.start_hour:
            raise ValueError("end_hour must be later than start_hour")
        return self


class CalendarBlockUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_hour: int | None = Field(default=None, ge=SCHEDULE_START_HOUR, le=SCHEDULE_END_HOUR - 1)
    end_hour: int | None = Field(default=None, ge=SCHEDULE_START_HOUR + 1, le=SCHEDULE_END_HOUR)
    goal_id: str | None = None
    is_recurring: bool | None = None
    recurrence_pattern: str | None = Field(default=None, max_length=80)
    alignment_status: str | None = Field(default=None, max_length=24)


class CalendarBlockResponse(BaseModel):
    id: str
    goal_id: str | None
    title: str
    day_of_week: int
    start_hour: int
    end_hour: int
    source: str
    is_recurring: bool
    recurrence_pattern: str | None
    completed: bool
    alignment_status: str

    model_config = {"from_attributes": True}


class WeekResponse(BaseModel):
    blocks: list[CalendarBlockResponse]


class SuggestResponse(BaseModel):
    blocks: list[CalendarBlockResponse]
    warnings: list[str] = Field(default_factory=list)


async def get_owned_block(db: AsyncSession, user: User, block_id: str) -> CalendarBlock:
    block = await db.scalar(select(CalendarBlock).where(CalendarBlock.id == block_id, CalendarBlock.user_id == user.id))
    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar block not found")
    return block


async def assert_owned_goal(db: AsyncSession, user: User, goal_id: str | None) -> None:
    if goal_id is None:
        return
    goal = await db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user.id))
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked goal not found")


def serialize_block(block: CalendarBlock) -> CalendarBlockResponse:
    return CalendarBlockResponse(
        id=block.id,
        goal_id=block.goal_id,
        title=block.title,
        day_of_week=block.day_of_week,
        start_hour=block.start_hour,
        end_hour=block.end_hour,
        source=block.source,
        is_recurring=block.is_recurring,
        recurrence_pattern=block.recurrence_pattern,
        completed=block.completed_at is not None,
        alignment_status=block.alignment_status,
    )


def validate_update_range(start_hour: int, end_hour: int) -> None:
    duration = end_hour - start_hour
    if start_hour < SCHEDULE_START_HOUR or end_hour > SCHEDULE_END_HOUR or duration < 1 or duration > MAX_BLOCK_HOURS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid block time range")


def block_duration(block: CalendarBlock) -> int:
    return max(0, block.end_hour - block.start_hour)


def day_capacity(day_of_week: int) -> int:
    return SUNDAY_MAX_HOURS if day_of_week == 6 else DAILY_MAX_HOURS


def overlaps(start_hour: int, end_hour: int, block: CalendarBlock) -> bool:
    return start_hour < block.end_hour and end_hour > block.start_hour


async def validate_block_slot(
    db: AsyncSession,
    user: User,
    day_of_week: int,
    start_hour: int,
    end_hour: int,
    exclude_block_id: str | None = None,
) -> None:
    validate_update_range(start_hour, end_hour)
    result = await db.scalars(select(CalendarBlock).where(CalendarBlock.user_id == user.id, CalendarBlock.day_of_week == day_of_week))
    blocks = [block for block in result if block.id != exclude_block_id]
    if any(overlaps(start_hour, end_hour, block) for block in blocks):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Calendar blocks cannot overlap.")

    scheduled_hours = sum(block_duration(block) for block in blocks) + (end_hour - start_hour)
    if scheduled_hours > day_capacity(day_of_week):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This day is at capacity. Add buffer time or choose another day.")


def day_warning_messages(blocks: list[CalendarBlock]) -> list[str]:
    warnings: list[str] = []
    day_labels = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    for day_index, label in enumerate(day_labels):
        scheduled = sum(block_duration(block) for block in blocks if block.day_of_week == day_index)
        if scheduled > day_capacity(day_index) * FULLNESS_WARNING_RATIO:
            warnings.append(f"{label} is over 70% full. Add buffer time.")
    return warnings


def mission_score(goal: Goal, mission_text: str) -> int:
    words = {word.strip(".,:;!?()[]{}").lower() for word in mission_text.split() if len(word.strip(".,:;!?()[]{}")) >= 4}
    if not words:
        return 0
    title = goal.title.lower()
    return sum(1 for word in words if word in title)


@router.get("/week", response_model=WeekResponse)
async def get_week(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WeekResponse:
    result = await db.scalars(
        select(CalendarBlock)
        .where(CalendarBlock.user_id == user.id)
        .order_by(CalendarBlock.day_of_week.asc(), CalendarBlock.start_hour.asc(), CalendarBlock.created_at.asc())
    )
    return WeekResponse(blocks=[serialize_block(block) for block in result])


@router.post("/blocks", response_model=CalendarBlockResponse, status_code=status.HTTP_201_CREATED)
async def create_block(
    payload: CalendarBlockCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CalendarBlockResponse:
    await assert_owned_goal(db, user, payload.goal_id)
    await validate_block_slot(db, user, payload.day_of_week, payload.start_hour, payload.end_hour)
    block = CalendarBlock(
        user_id=user.id,
        goal_id=payload.goal_id,
        title=payload.title.strip(),
        day_of_week=payload.day_of_week,
        start_hour=payload.start_hour,
        end_hour=payload.end_hour,
        source="manual",
        is_recurring=payload.is_recurring,
        recurrence_pattern=payload.recurrence_pattern.strip() if payload.recurrence_pattern else None,
        alignment_status=payload.alignment_status.strip() or "unknown",
    )
    db.add(block)
    await db.commit()
    await db.refresh(block)
    return serialize_block(block)


@router.patch("/blocks/{block_id}", response_model=CalendarBlockResponse)
async def update_block(
    block_id: str,
    payload: CalendarBlockUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CalendarBlockResponse:
    block = await get_owned_block(db, user, block_id)
    await assert_owned_goal(db, user, payload.goal_id)

    if payload.title is not None:
        block.title = payload.title.strip()
    if payload.day_of_week is not None:
        block.day_of_week = payload.day_of_week
    if payload.start_hour is not None:
        block.start_hour = payload.start_hour
    if payload.end_hour is not None:
        block.end_hour = payload.end_hour
    if payload.goal_id is not None:
        block.goal_id = payload.goal_id
    if payload.is_recurring is not None:
        block.is_recurring = payload.is_recurring
    if payload.recurrence_pattern is not None:
        block.recurrence_pattern = payload.recurrence_pattern.strip() or None
    if payload.alignment_status is not None:
        block.alignment_status = payload.alignment_status.strip() or "unknown"

    await validate_block_slot(db, user, block.day_of_week, block.start_hour, block.end_hour, exclude_block_id=block.id)
    db.add(block)
    await db.commit()
    await db.refresh(block)
    return serialize_block(block)


@router.patch("/blocks/{block_id}/complete", response_model=CalendarBlockResponse)
async def complete_block(
    block_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CalendarBlockResponse:
    block = await get_owned_block(db, user, block_id)
    block.completed_at = None if block.completed_at else now_utc()
    db.add(block)
    await db.commit()
    await db.refresh(block)
    return serialize_block(block)


@router.delete("/blocks/{block_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_block(
    block_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    block = await get_owned_block(db, user, block_id)
    await db.delete(block)
    await db.commit()


@router.delete("/week/generated", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def clear_generated_week(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await db.execute(delete(CalendarBlock).where(CalendarBlock.user_id == user.id, CalendarBlock.source == "oracle_suggested"))
    await db.commit()


@router.post("/suggest", response_model=SuggestResponse)
async def suggest_schedule(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuggestResponse:
    await db.execute(delete(CalendarBlock).where(CalendarBlock.user_id == user.id, CalendarBlock.source == "oracle_suggested"))
    await db.flush()

    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    mission_text = " ".join(
        value
        for value in [
            profile.life_mission if profile else "",
            profile.vision_3_5_year if profile else "",
            profile.one_year_goal if profile else "",
        ]
        if value
    )
    goal_result = await db.scalars(
        select(Goal)
        .where(
            Goal.user_id == user.id,
            Goal.horizon.in_(["daily_part_1", "daily_part_2"]),
            Goal.is_complete.is_(False),
        )
        .order_by(Goal.created_at.asc())
        .limit(50)
    )
    goals = sorted(list(goal_result), key=lambda goal: (-goal.priority, -mission_score(goal, mission_text), goal.created_at))[:24]
    if not goals:
        return SuggestResponse(blocks=[], warnings=["Add daily priority or bonus tasks from Goals before generating a week."])

    block_result = await db.scalars(select(CalendarBlock).where(CalendarBlock.user_id == user.id))
    fixed_blocks = list(block_result)
    day_hours = {day_index: 0 for day_index in range(7)}
    occupied: set[tuple[int, int]] = set()
    for block in fixed_blocks:
        day_hours[block.day_of_week] = day_hours.get(block.day_of_week, 0) + block_duration(block)
        for hour in range(block.start_hour, block.end_hour):
            occupied.add((block.day_of_week, hour))

    created: list[CalendarBlock] = []
    unplaced: list[str] = []
    for goal in goals:
        duration = min(MAX_BLOCK_HOURS, max(1, min(goal.target_count, 2 if goal.priority > 0 else 1)))
        placed = False
        candidate_days = list(PLANNER_DAYS)
        if goal.priority <= 0:
            candidate_days = sorted(candidate_days, key=lambda day_index: day_hours[day_index])

        for day in candidate_days:
            if day_hours[day] + duration > day_capacity(day):
                continue
            for hour in range(SCHEDULE_START_HOUR, SCHEDULE_END_HOUR - duration + 1):
                slots = [(day, slot_hour) for slot_hour in range(hour, hour + duration)]
                if any(slot in occupied for slot in slots):
                    continue
                block = CalendarBlock(
                    user_id=user.id,
                    goal_id=goal.id,
                    title=goal.title,
                    day_of_week=day,
                    start_hour=hour,
                    end_hour=hour + duration,
                    source="oracle_suggested",
                    alignment_status="priority" if goal.priority > 0 else "bonus",
                )
                db.add(block)
                created.append(block)
                for slot in slots:
                    occupied.add(slot)
                day_hours[day] += duration
                placed = True
                break
            if placed:
                break

        if not placed:
            unplaced.append(goal.title)

    await db.commit()
    for block in created:
        await db.refresh(block)

    warnings = day_warning_messages([*fixed_blocks, *created])
    if unplaced:
        warnings.append(f"{len(unplaced)} task(s) could not fit without overlap or exceeding the daily cap.")

    return SuggestResponse(blocks=[serialize_block(block) for block in created], warnings=warnings)
