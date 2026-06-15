from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import OracleConversation, User
from app.modules.oracle.client import OracleClient, get_oracle_client

router = APIRouter()


class OraclePrompt(BaseModel):
    message: str
    context: dict[str, str] = {}


class OracleResponse(BaseModel):
    response: str
    provider: str
    degraded: bool


class BreakdownPrompt(BaseModel):
    title: str
    horizon: str
    child_horizon: str


class BreakdownResponse(BaseModel):
    response: str
    tasks: list[str]
    provider: str
    degraded: bool


@router.get("/status")
async def status(
    user: Annotated[User, Depends(get_current_user)],
    oracle: Annotated[OracleClient, Depends(get_oracle_client)],
) -> dict[str, str | bool]:
    return {
        "provider": "openai" if oracle.configured else "fallback",
        "configured": oracle.configured,
        "model": oracle.model_name,
    }


@router.post("/interrogate", response_model=OracleResponse)
async def interrogate(
    payload: OraclePrompt,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    oracle: Annotated[OracleClient, Depends(get_oracle_client)],
) -> OracleResponse:
    prompt = (
        "Interrogate this vague intent and turn it into a concrete mission. "
        "Ask one sharp follow-up question if details are missing. "
        "If enough detail exists, propose 1-3 goals and ask whether to create them manually or automatically.\n\n"
        f"Operator input: {payload.message}\nContext: {payload.context}"
    )
    result = await oracle.generate(prompt)
    db.add(
        OracleConversation(
            user_id=user.id,
            messages={"input": payload.message, "context": payload.context, "output": result.text, "provider": result.provider},
        )
    )
    await db.commit()
    return OracleResponse(response=result.text, provider=result.provider, degraded=result.degraded)


@router.post("/breakdown-goal", response_model=BreakdownResponse)
async def breakdown_goal(
    payload: BreakdownPrompt,
    user: Annotated[User, Depends(get_current_user)],
    oracle: Annotated[OracleClient, Depends(get_oracle_client)],
) -> BreakdownResponse:
    result = await oracle.breakdown_goal(payload.title, payload.horizon, payload.child_horizon)
    return BreakdownResponse(
        response=result.text,
        tasks=oracle.parse_tasks(result.text, payload.title),
        provider=result.provider,
        degraded=result.degraded,
    )


@router.post("/schedule-review", response_model=OracleResponse)
async def schedule_review(
    payload: OraclePrompt,
    user: Annotated[User, Depends(get_current_user)],
    oracle: Annotated[OracleClient, Depends(get_oracle_client)],
) -> OracleResponse:
    result = await oracle.generate(
        "Review this weekly schedule and suggest sharper execution order:\n\n" + payload.message
    )
    return OracleResponse(response=result.text, provider=result.provider, degraded=result.degraded)
