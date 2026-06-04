from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import OnboardingAnswer, User, UserProfile, now_utc

router = APIRouter()


class OnboardingPayload(BaseModel):
    life_mission: str = Field(default="", max_length=4000)
    vision_3_5_year: str = Field(default="", max_length=4000)
    one_year_goal: str = Field(default="", max_length=4000)
    monthly_goals: list[str] = Field(default_factory=list, max_length=8)
    character_class: str | None = Field(default=None, max_length=40)


class OnboardingResponse(OnboardingPayload):
    completed: bool


async def get_profile(db: AsyncSession, user: User) -> UserProfile:
    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        await db.flush()
    return profile


@router.get("/state", response_model=OnboardingResponse)
async def get_onboarding_state(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OnboardingResponse:
    profile = await get_profile(db, user)
    monthly = await db.scalar(
        select(OnboardingAnswer.answer).where(OnboardingAnswer.user_id == user.id, OnboardingAnswer.question_key == "monthly_goals")
    )
    return OnboardingResponse(
        life_mission=profile.life_mission or "",
        vision_3_5_year=profile.vision_3_5_year or "",
        one_year_goal=profile.one_year_goal or "",
        monthly_goals=[item for item in (monthly or "").split("\n") if item.strip()],
        character_class=None,
        completed=profile.onboarding_completed_at is not None,
    )


@router.put("/state", response_model=OnboardingResponse)
async def save_onboarding_state(
    payload: OnboardingPayload,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OnboardingResponse:
    profile = await get_profile(db, user)
    profile.life_mission = payload.life_mission.strip()
    profile.vision_3_5_year = payload.vision_3_5_year.strip()
    profile.one_year_goal = payload.one_year_goal.strip()
    profile.onboarding_completed_at = now_utc()

    monthly_text = "\n".join(goal.strip() for goal in payload.monthly_goals if goal.strip())
    monthly = await db.scalar(
        select(OnboardingAnswer).where(OnboardingAnswer.user_id == user.id, OnboardingAnswer.question_key == "monthly_goals")
    )
    if monthly is None:
        monthly = OnboardingAnswer(user_id=user.id, question_key="monthly_goals", answer=monthly_text)
    else:
        monthly.answer = monthly_text
    db.add_all([profile, monthly])
    await db.commit()
    return await get_onboarding_state(user, db)
