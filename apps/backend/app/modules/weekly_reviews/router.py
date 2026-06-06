from __future__ import annotations

from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User, WeeklyReview, WeeklyReviewExport, now_utc

router = APIRouter()


class WeeklyReviewPayload(BaseModel):
    week_ending: date
    wins: str = Field(default="", max_length=5000)
    friction: str = Field(default="", max_length=5000)
    alignment: str = Field(default="", max_length=5000)
    directive: str = Field(default="", max_length=5000)
    completion_rate: int = Field(default=0, ge=0, le=100)
    xp_gained: int = Field(default=0, ge=0)
    streak: int = Field(default=0, ge=0)
    lock: bool = False


class WeeklyReviewResponse(BaseModel):
    id: str
    week_ending: date
    wins: str
    friction: str
    alignment: str
    directive: str
    completion_rate: int
    xp_gained: int
    streak: int
    locked: bool
    updated_at: str
    summary: str


class CompareResponse(BaseModel):
    left: WeeklyReviewResponse
    right: WeeklyReviewResponse
    completion_rate_delta: int
    xp_gained_delta: int
    streak_delta: int


class ExportPayload(BaseModel):
    review_ids: list[str] = Field(min_length=1, max_length=20)
    sections: list[str] = Field(default_factory=lambda: ["wins", "friction", "alignment", "directive", "metrics"])


class ExportResponse(BaseModel):
    id: str
    filename: str
    settings: dict
    created_at: str


def weekly_summary(review: WeeklyReview) -> str:
    completion_label = "full clear" if review.completion_rate >= 90 else "partial progress" if review.completion_rate >= 50 else "reset window"
    return (
        f"{review.week_ending}: {completion_label}. "
        f"Wins point to {review.wins[:120] or 'no captured wins yet'}. "
        f"Friction to address: {review.friction[:120] or 'none recorded'}. "
        f"Next directive: {review.directive[:160] or 'define one priority for the next week'}."
    )


def serialize(review: WeeklyReview) -> WeeklyReviewResponse:
    return WeeklyReviewResponse(
        id=review.id,
        week_ending=review.week_ending,
        wins=review.wins,
        friction=review.friction,
        alignment=review.alignment,
        directive=review.directive,
        completion_rate=review.completion_rate,
        xp_gained=review.xp_gained,
        streak=review.streak,
        locked=review.locked_at is not None,
        updated_at=review.updated_at.isoformat(),
        summary=weekly_summary(review),
    )


async def get_review_or_404(db: AsyncSession, user: User, review_id: str) -> WeeklyReview:
    review = await db.scalar(select(WeeklyReview).where(WeeklyReview.id == review_id, WeeklyReview.user_id == user.id))
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Weekly review not found")
    return review


@router.get("/latest", response_model=Optional[WeeklyReviewResponse])
async def latest_review(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Optional[WeeklyReviewResponse]:
    review = await db.scalar(select(WeeklyReview).where(WeeklyReview.user_id == user.id).order_by(WeeklyReview.week_ending.desc()))
    return serialize(review) if review else None


@router.get("", response_model=list[WeeklyReviewResponse])
async def list_reviews(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[WeeklyReviewResponse]:
    result = await db.scalars(select(WeeklyReview).where(WeeklyReview.user_id == user.id).order_by(WeeklyReview.week_ending.desc()))
    return [serialize(review) for review in result]


@router.put("", response_model=WeeklyReviewResponse)
async def upsert_review(
    payload: WeeklyReviewPayload,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WeeklyReviewResponse:
    review = await db.scalar(select(WeeklyReview).where(WeeklyReview.user_id == user.id, WeeklyReview.week_ending == payload.week_ending))
    if review is None:
        review = WeeklyReview(user_id=user.id, week_ending=payload.week_ending)
    review.wins = payload.wins.strip()
    review.friction = payload.friction.strip()
    review.alignment = payload.alignment.strip()
    review.directive = payload.directive.strip()
    review.completion_rate = payload.completion_rate
    review.xp_gained = payload.xp_gained
    review.streak = payload.streak
    review.locked_at = now_utc() if payload.lock else None
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return serialize(review)


@router.get("/compare", response_model=CompareResponse)
async def compare_reviews(
    left_id: str,
    right_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CompareResponse:
    left = await get_review_or_404(db, user, left_id)
    right = await get_review_or_404(db, user, right_id)
    return CompareResponse(
        left=serialize(left),
        right=serialize(right),
        completion_rate_delta=right.completion_rate - left.completion_rate,
        xp_gained_delta=right.xp_gained - left.xp_gained,
        streak_delta=right.streak - left.streak,
    )


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_review(
    review_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    review = await get_review_or_404(db, user, review_id)
    await db.delete(review)
    await db.commit()


@router.post("/exports", response_model=ExportResponse, status_code=status.HTTP_201_CREATED)
async def create_export(
    payload: ExportPayload,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExportResponse:
    reviews = list(
        await db.scalars(select(WeeklyReview).where(WeeklyReview.user_id == user.id, WeeklyReview.id.in_(payload.review_ids)))
    )
    if len(reviews) != len(set(payload.review_ids)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more weekly reviews were not found")

    filename = f"operator-weekly-review-{now_utc().strftime('%Y%m%d-%H%M%S')}.pdf"
    export = WeeklyReviewExport(
        user_id=user.id,
        review_id=payload.review_ids[0] if len(payload.review_ids) == 1 else None,
        filename=filename,
        settings={
            "review_ids": payload.review_ids,
            "sections": payload.sections,
            "kind": "single" if len(payload.review_ids) == 1 else "multi",
            "summaries": [weekly_summary(review) for review in reviews],
        },
    )
    db.add(export)
    await db.commit()
    await db.refresh(export)
    return ExportResponse(id=export.id, filename=export.filename, settings=export.settings, created_at=export.created_at.isoformat())


@router.get("/exports", response_model=list[ExportResponse])
async def list_exports(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ExportResponse]:
    result = await db.scalars(
        select(WeeklyReviewExport).where(WeeklyReviewExport.user_id == user.id).order_by(WeeklyReviewExport.created_at.desc())
    )
    return [
        ExportResponse(id=export.id, filename=export.filename, settings=export.settings, created_at=export.created_at.isoformat())
        for export in result
    ]
