from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import CalendarBlock, Goal, User, now_utc

router = APIRouter()

SCHEDULE_START_HOUR = 7
SCHEDULE_END_HOUR = 22


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
    if start_hour < SCHEDULE_START_HOUR or end_hour > SCHEDULE_END_HOUR or end_hour <= start_hour:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid block time range")


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

    validate_update_range(block.start_hour, block.end_hour)
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


@router.post("/suggest", response_model=SuggestResponse)
async def suggest_schedule(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuggestResponse:
    goal_result = await db.scalars(
        select(Goal)
        .where(
            Goal.user_id == user.id,
            Goal.horizon.in_(["weekly", "daily_part_1", "daily_part_2"]),
            Goal.is_complete.is_(False),
        )
        .order_by(Goal.priority.desc(), Goal.created_at.asc())
        .limit(10)
    )
    goals = list(goal_result)
    if not goals:
        return SuggestResponse(blocks=[])

    block_result = await db.scalars(select(CalendarBlock).where(CalendarBlock.user_id == user.id))
    occupied = {
        (block.day_of_week, hour)
        for block in block_result
        for hour in range(block.start_hour, block.end_hour)
    }

    created: list[CalendarBlock] = []
    day = 0
    hour = SCHEDULE_START_HOUR
    for goal in goals:
        placed = False
        for _ in range(7 * (SCHEDULE_END_HOUR - SCHEDULE_START_HOUR)):
            slot = (day, hour)
            if slot not in occupied:
                block = CalendarBlock(
                    user_id=user.id,
                    goal_id=goal.id,
                    title=goal.title,
                    day_of_week=day,
                    start_hour=hour,
                    end_hour=hour + 1,
                    source="oracle_suggested",
                    alignment_status="aligned" if goal.priority > 0 else "unknown",
                )
                db.add(block)
                created.append(block)
                occupied.add(slot)
                placed = True
                day = (day + 1) % 7
                break

            hour += 1
            if hour >= SCHEDULE_END_HOUR:
                hour = SCHEDULE_START_HOUR
                day = (day + 1) % 7

        if not placed:
            break

    await db.commit()
    for block in created:
        await db.refresh(block)

    return SuggestResponse(blocks=[serialize_block(block) for block in created])
